"""Main paper retrieval orchestration.

Tries multiple sources in priority order to find and download PDFs.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import httpx

from .config import Config
from .logger import RetrievalLogger
from .rate_limiter import RateLimiter


class RetrievalStatus(Enum):
    """Status of a retrieval attempt."""
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    ERROR = "error"
    SKIPPED = "skipped"
    FAILED = "failed"  # Alias for NOT_FOUND for CLI compatibility


@dataclass
class RetrievalResult:
    """Result of a paper retrieval attempt."""
    doi: str | None
    title: str
    status: RetrievalStatus
    source: str | None = None
    pdf_path: str | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = None
    attempts: list[dict[str, Any]] | None = None  # History of attempted sources


class PaperRetriever:
    """Main orchestrator for paper PDF retrieval.

    Tries multiple sources in priority order to find PDFs.

    Example:
        >>> config = Config.load("config.yaml")
        >>> retriever = PaperRetriever(config)
        >>> result = await retriever.retrieve(doi="10.1234/example")
        >>> print(result.pdf_path)
    """

    def __init__(self, config: Config | None = None):
        """Initialize the paper retriever.

        Args:
            config: Configuration object (loads default if None)
        """
        self.config = config or Config.load()
        self.rate_limiter = RateLimiter(self.config.rate_limits)
        self.clients = self._init_clients()

    def _init_clients(self) -> dict[str, Any]:
        """Initialize all API clients."""
        from .clients import (
            ArxivClient,
            BioRxivClient,
            CrossRefClient,
            OpenAlexClient,
            PMCClient,
            SemanticScholarClient,
            UnpaywallClient,
        )

        clients: dict[str, Any] = {
            "arxiv": ArxivClient(),
            "crossref": CrossRefClient(email=self.config.email),
            "semantic_scholar": SemanticScholarClient(
                api_key=self.config.api_keys.get("semantic_scholar")
            ),
            "pmc": PMCClient(
                api_key=self.config.api_keys.get("ncbi"),
                email=self.config.email,
            ),
            "biorxiv": BioRxivClient(),
            "openalex": OpenAlexClient(email=self.config.email),
        }

        # Unpaywall requires email
        if self.config.email:
            clients["unpaywall"] = UnpaywallClient(email=self.config.email)

        # Initialize institutional client if configured
        inst_config = self.config.institutional
        if inst_config.get("enabled"):
            from .clients import InstitutionalAccessClient
            clients["institutional"] = InstitutionalAccessClient(
                proxy_url=inst_config.get("proxy_url"),
                vpn_enabled=inst_config.get("vpn_enabled", False),
                vpn_script=inst_config.get("vpn_script"),
                cookies_file=inst_config.get("cookies_file", ".institutional_cookies.pkl"),
                download_dir=self.config.download.get("output_dir", "./downloads"),
            )

        # Initialize web search client
        if self.config.is_source_enabled("web_search"):
            from .clients import WebSearchClient
            clients["web_search"] = WebSearchClient(enabled=True)

        # Initialize unofficial clients if disclaimer accepted
        if self.config.is_unofficial_enabled():
            if self.config.is_source_enabled("scihub"):
                from .clients import ScihubClient
                clients["scihub"] = ScihubClient(timeout=60.0, max_retries=2)

            if self.config.is_source_enabled("libgen"):
                from .clients import LibGenClient
                clients["libgen"] = LibGenClient(timeout=60.0, max_retries=2)

        return clients

    async def retrieve(
        self,
        doi: str | None = None,
        title: str | None = None,
        output_dir: Path | None = None,
        verbose: bool = True,
    ) -> RetrievalResult:
        """Retrieve PDF for a paper.

        Args:
            doi: Paper DOI
            title: Paper title
            output_dir: Override output directory
            verbose: Show progress in console

        Returns:
            RetrievalResult with status and file path
        """
        if not doi and not title:
            return RetrievalResult(
                doi=None,
                title="",
                status=RetrievalStatus.ERROR,
                error="Must provide DOI or title",
            )

        # Setup output directory
        out_dir = Path(output_dir) if output_dir else Path(self.config.download.get("output_dir", "./downloads"))
        out_dir.mkdir(parents=True, exist_ok=True)

        # Create logger
        logger = RetrievalLogger(out_dir, doi, title, console_enabled=verbose)

        # Resolve metadata if needed
        metadata = await self._resolve_metadata(doi, title)
        resolved_doi = metadata.get("doi") if metadata else doi
        resolved_title = metadata.get("title") if metadata else title
        year = metadata.get("year") if metadata else None

        # Show header
        logger.header(resolved_doi, resolved_title, str(year) if year else None)

        # Generate output path
        output_path = self._get_output_path(metadata or {"doi": doi, "title": title}, out_dir)

        # Check if already downloaded
        if self.config.download.get("skip_existing") and output_path.exists():
            logger.final_result(True, "cached", str(output_path))
            return RetrievalResult(
                doi=resolved_doi,
                title=resolved_title or "",
                status=RetrievalStatus.SKIPPED,
                source="cached",
                pdf_path=str(output_path),
                metadata=metadata,
            )

        # Try sources in priority order
        sources = self.config.get_sorted_sources()
        total_sources = sum(1 for s in sources if self.config.is_source_enabled(s))

        source_index = 0
        for source_name in sources:
            if not self.config.is_source_enabled(source_name):
                continue

            # Skip unofficial sources if not enabled
            if source_name in ("scihub", "libgen") and not self.config.is_unofficial_enabled():
                continue

            source_index += 1
            logger.source_start(source_index, total_sources, source_name)

            await self.rate_limiter.wait(source_name)

            result, reason = await self._try_source(
                source_name,
                resolved_doi,
                resolved_title or title or "",
                metadata or {},
                output_path,
                logger,
            )

            if result and result.status == RetrievalStatus.SUCCESS:
                logger.source_result(source_index, total_sources, source_name, True, reason, result.pdf_path)
                logger.final_result(True, source_name, result.pdf_path)
                result.metadata = metadata
                return result
            else:
                logger.source_result(source_index, total_sources, source_name, False, reason)

        logger.final_result(False)
        return RetrievalResult(
            doi=resolved_doi,
            title=resolved_title or title or "",
            status=RetrievalStatus.NOT_FOUND,
            error="PDF not found in any source",
            metadata=metadata,
        )

    async def _resolve_metadata(
        self,
        doi: str | None = None,
        title: str | None = None
    ) -> dict[str, Any] | None:
        """Resolve full metadata from DOI or title."""
        crossref = self.clients.get("crossref")
        if not crossref:
            return {"doi": doi, "title": title}

        if doi:
            try:
                await self.rate_limiter.wait("crossref")
                work = await crossref.get_work(doi)
                if work:
                    return self._extract_crossref_metadata(work)
            except Exception:
                pass

        if title:
            try:
                await self.rate_limiter.wait("crossref")
                results = await crossref.search_title(title)
                if results:
                    best_match = self._find_best_title_match(title, results)
                    if best_match:
                        return self._extract_crossref_metadata(best_match)
            except Exception:
                pass

        return {"doi": doi, "title": title}

    def _extract_crossref_metadata(self, work: dict[str, Any]) -> dict[str, Any]:
        """Extract metadata from CrossRef work object."""
        titles = work.get("title", [])
        title = titles[0] if titles else None

        authors = []
        for author in work.get("author", []):
            name = f"{author.get('given', '')} {author.get('family', '')}".strip()
            if name:
                authors.append({
                    "name": name,
                    "given": author.get("given"),
                    "family": author.get("family"),
                })

        # Get year from published date
        date_parts = work.get("published", {}).get("date-parts", [[]])
        year = date_parts[0][0] if date_parts and date_parts[0] else None

        return {
            "doi": work.get("DOI"),
            "title": title,
            "authors": authors,
            "year": year,
            "venue": work.get("container-title", [None])[0] if work.get("container-title") else None,
            "publisher": work.get("publisher"),
            "type": work.get("type"),
        }

    def _find_best_title_match(
        self,
        query_title: str,
        results: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Find the best matching result for a title query."""
        query_normalized = self._normalize_title(query_title)

        best_match = None
        best_score = 0.0

        for result in results:
            titles = result.get("title", [])
            if not titles:
                continue

            result_title = titles[0] if isinstance(titles, list) else titles
            result_normalized = self._normalize_title(result_title)

            query_words = set(query_normalized.split())
            result_words = set(result_normalized.split())
            common = len(query_words & result_words)
            total = len(query_words | result_words)
            score = common / total if total > 0 else 0

            if score > best_score:
                best_score = score
                best_match = result

        return best_match if best_score >= 0.5 else None

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalize a title for comparison."""
        normalized = re.sub(r"[^\w\s]", "", title.lower())
        return " ".join(normalized.split())

    def _get_output_path(self, metadata: dict[str, Any], output_dir: Path) -> Path:
        """Generate output file path from metadata."""
        # Get components
        authors = metadata.get("authors", [])
        first_author = ""
        if authors:
            if isinstance(authors[0], dict):
                first_author = authors[0].get("family", "") or authors[0].get("name", "").split()[-1]
            else:
                first_author = str(authors[0]).split()[-1]

        year = str(metadata.get("year", "")) if metadata.get("year") else ""
        title = metadata.get("title", "") or ""

        # Clean title
        max_len = self.config.download.get("max_title_length", 50)
        title_short = re.sub(r"[^\w\s-]", "", title)[:max_len].strip()

        # Build filename
        parts = [p for p in [first_author, year, title_short] if p]
        if parts:
            filename = "_".join(parts).replace(" ", "_") + ".pdf"
        elif metadata.get("doi"):
            filename = metadata["doi"].replace("/", "_") + ".pdf"
        else:
            filename = "paper.pdf"

        return output_dir / filename

    async def _try_source(
        self,
        source: str,
        doi: str | None,
        title: str,
        metadata: dict[str, Any],
        output_path: Path,
        logger: RetrievalLogger,
    ) -> tuple[RetrievalResult | None, str]:
        """Try to retrieve PDF from a specific source."""
        client = self.clients.get(source)
        if not client:
            return None, "client not configured"

        try:
            if source == "unpaywall":
                return await self._try_unpaywall(client, doi, title, output_path, logger)

            elif source == "arxiv":
                return await self._try_arxiv(client, doi, title, output_path, logger)

            elif source == "pmc":
                return await self._try_pmc(client, doi, title, output_path, logger)

            elif source == "biorxiv":
                return await self._try_biorxiv(client, doi, title, output_path, logger)

            elif source == "semantic_scholar":
                return await self._try_semantic_scholar(client, doi, title, output_path, logger)

            elif source == "openalex":
                return await self._try_openalex(client, doi, title, output_path, logger)

            elif source == "institutional":
                return await self._try_institutional(client, doi, title, output_path, logger)

            elif source == "web_search":
                return await self._try_web_search(client, doi, title, metadata, output_path, logger)

            elif source == "scihub":
                return await self._try_scihub(client, doi, title, output_path, logger)

            elif source == "libgen":
                return await self._try_libgen(client, doi, title, output_path, logger)

        except Exception as e:
            logger.error(source, str(e))
            return None, f"error: {e}"

        return None, "unknown source"

    async def _try_unpaywall(self, client, doi, title, output_path, logger) -> tuple[RetrievalResult | None, str]:
        """Try Unpaywall source."""
        if not doi:
            return None, "no DOI provided"

        logger.detail(f"Checking OA status for {doi}")
        pdf_url = await client.get_pdf_url(doi)

        if not pdf_url:
            return None, "no OA version found"

        logger.detail(f"Found PDF: {pdf_url}")
        if await self._download_pdf(pdf_url, output_path):
            return RetrievalResult(
                doi=doi, title=title, status=RetrievalStatus.SUCCESS,
                source="unpaywall", pdf_path=str(output_path),
            ), "downloaded"
        return None, "PDF download failed"

    async def _try_arxiv(self, client, doi, title, output_path, logger) -> tuple[RetrievalResult | None, str]:
        """Try arXiv source."""
        # Check if arXiv paper by DOI
        if doi and "arxiv" in doi.lower():
            logger.detail(f"arXiv DOI detected: {doi}")
            # Extract arXiv ID from DOI
            arxiv_id = re.search(r"arxiv\.(\d+\.\d+)", doi.lower())
            if arxiv_id:
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id.group(1)}.pdf"
                logger.detail(f"PDF URL: {pdf_url}")
                if await self._download_pdf(pdf_url, output_path):
                    return RetrievalResult(
                        doi=doi, title=title, status=RetrievalStatus.SUCCESS,
                        source="arxiv", pdf_path=str(output_path),
                    ), "downloaded"

        # Search by title using arXiv search API
        logger.detail(f"Searching by title: {title[:50]}...")
        # Use quoted search for better exact matching
        quoted_title = f'"{title}"'
        results = await client.search(quoted_title, limit=5)
        for metadata in results:
            arxiv_id = metadata.get("arxiv_id")
            if arxiv_id and self._titles_match(title, metadata.get("title", "")):
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                logger.detail(f"Title match found, PDF: {pdf_url}")
                if await self._download_pdf(pdf_url, output_path):
                    return RetrievalResult(
                        doi=doi, title=title, status=RetrievalStatus.SUCCESS,
                        source="arxiv", pdf_path=str(output_path),
                    ), "downloaded"

        return None, "not an arXiv paper"

    async def _try_pmc(self, client, doi, title, output_path, logger) -> tuple[RetrievalResult | None, str]:
        """Try PMC source."""
        if not doi:
            return None, "no DOI provided"

        logger.detail(f"Looking up PMC ID for {doi}")
        pmcid = await client.doi_to_pmcid(doi)

        if not pmcid:
            return None, "no PMC ID for this DOI"

        logger.detail(f"Found PMC ID: {pmcid}")
        pdf_url = await client.get_pdf_url(pmcid)

        if not pdf_url:
            return None, "PMC entry has no PDF"

        logger.detail(f"PDF URL: {pdf_url}")
        if await self._download_pdf(pdf_url, output_path):
            return RetrievalResult(
                doi=doi, title=title, status=RetrievalStatus.SUCCESS,
                source="pmc", pdf_path=str(output_path),
            ), "downloaded"
        return None, "PDF download failed"

    async def _try_biorxiv(self, client, doi, title, output_path, logger) -> tuple[RetrievalResult | None, str]:
        """Try bioRxiv source."""
        if not doi:
            return None, "no DOI provided"
        if not doi.startswith("10.1101"):
            return None, "not a bioRxiv DOI"

        logger.detail(f"Checking bioRxiv for {doi}")
        result = await client.get_preprint(doi)

        if not result or not result.get("pdf_url"):
            return None, "preprint not found"

        logger.detail(f"PDF URL: {result['pdf_url']}")
        if await self._download_pdf(result["pdf_url"], output_path):
            return RetrievalResult(
                doi=doi, title=title, status=RetrievalStatus.SUCCESS,
                source=result.get("server", "biorxiv"), pdf_path=str(output_path),
            ), "downloaded"
        return None, "PDF download failed"

    async def _try_semantic_scholar(self, client, doi, title, output_path, logger) -> tuple[RetrievalResult | None, str]:
        """Try Semantic Scholar source."""
        result = None

        if doi:
            logger.detail(f"Looking up paper by DOI: {doi}")
            result = await client.get_paper_metadata(f"DOI:{doi}")

        if not result or not result.get("pdf_url"):
            logger.detail(f"Searching by title: {title[:50]}...")
            results = await client.search(title, limit=5)
            for r in results:
                if r.get("pdf_url") and self._titles_match(title, r.get("title", "")):
                    result = r
                    break

        if not result or not result.get("pdf_url"):
            return None, "no open access PDF"

        pdf_url = result["pdf_url"]
        logger.detail(f"PDF URL: {pdf_url}")

        if await self._download_pdf(pdf_url, output_path):
            return RetrievalResult(
                doi=doi, title=title, status=RetrievalStatus.SUCCESS,
                source="semantic_scholar", pdf_path=str(output_path),
            ), "downloaded"
        return None, "PDF download failed"

    async def _try_openalex(self, client, doi, title, output_path, logger) -> tuple[RetrievalResult | None, str]:
        """Try OpenAlex source."""
        result = None

        if doi:
            logger.detail(f"Looking up work by DOI: {doi}")
            result = await client.get_paper_metadata(doi)

        if not result:
            logger.detail(f"Searching by title: {title[:50]}...")
            results = await client.search(title, limit=5)
            for r in results:
                if self._titles_match(title, r.get("title", "")):
                    result = r
                    break

        if not result:
            return None, "work not found"

        # Check for open access PDF - try pdf_url first, then open_access.oa_url
        oa_url = result.get("pdf_url") or result.get("open_access", {}).get("oa_url")
        if not oa_url:
            return None, "no OA URL"

        logger.detail(f"OA URL: {oa_url}")
        if await self._download_pdf(oa_url, output_path):
            return RetrievalResult(
                doi=doi, title=title, status=RetrievalStatus.SUCCESS,
                source="openalex", pdf_path=str(output_path),
            ), "downloaded"
        return None, "PDF download failed"

    async def _try_institutional(self, client, doi, title, output_path, logger) -> tuple[RetrievalResult | None, str]:
        """Try institutional access."""
        if not doi:
            return None, "no DOI provided"
        if not client.is_authenticated():
            return None, "not authenticated"

        logger.detail(f"Accessing via EZProxy: {doi}")
        if await client.download_pdf(doi, output_path):
            return RetrievalResult(
                doi=doi, title=title, status=RetrievalStatus.SUCCESS,
                source="institutional", pdf_path=str(output_path),
            ), "downloaded"
        return None, "institutional download failed"

    async def _try_web_search(self, client, doi, title, metadata, output_path, logger) -> tuple[RetrievalResult | None, str]:
        """Try web search."""
        authors = metadata.get("authors", [])
        author_names = [a.get("family", "") or a.get("name", "") for a in authors if isinstance(a, dict)]

        logger.detail(f"Web searching for: {title[:50]}...")
        result = await client.search_for_pdf(title=title, doi=doi, authors=author_names)

        if not result or not result.get("pdf_url"):
            return None, "no PDF found via web search"

        logger.detail(f"Found: {result['pdf_url']}")
        if await self._download_pdf(result["pdf_url"], output_path):
            return RetrievalResult(
                doi=doi, title=title, status=RetrievalStatus.SUCCESS,
                source="web_search", pdf_path=str(output_path),
            ), "downloaded"
        return None, "PDF download failed"

    async def _try_scihub(self, client, doi, title, output_path, logger) -> tuple[RetrievalResult | None, str]:
        """Try Sci-Hub (unofficial)."""
        logger.detail("Trying Sci-Hub mirrors...")
        result = None

        if doi:
            result = await client.download_by_doi(doi, output_path)
        if not result and title:
            result = await client.download_by_title(title, output_path)

        if result and result.get("pdf_path"):
            return RetrievalResult(
                doi=doi, title=title, status=RetrievalStatus.SUCCESS,
                source="scihub", pdf_path=result["pdf_path"],
            ), "downloaded"
        return None, "not available or bot protection"

    async def _try_libgen(self, client, doi, title, output_path, logger) -> tuple[RetrievalResult | None, str]:
        """Try LibGen (unofficial)."""
        logger.detail("Trying LibGen mirrors...")
        result = None

        if doi:
            result = await client.download_by_doi(doi, output_path)
        if not result and title:
            result = await client.download_by_title(title, output_path)

        if result and result.get("pdf_path"):
            return RetrievalResult(
                doi=doi, title=title, status=RetrievalStatus.SUCCESS,
                source="libgen", pdf_path=result["pdf_path"],
            ), "downloaded"
        return None, "not available or connection failed"

    def _titles_match(self, title1: str, title2: str) -> bool:
        """Check if two titles are similar enough."""
        norm1 = self._normalize_title(title1)
        norm2 = self._normalize_title(title2)

        words1 = set(norm1.split())
        words2 = set(norm2.split())

        if not words1 or not words2:
            return False

        common = len(words1 & words2)
        total = len(words1 | words2)
        return common / total >= 0.6 if total > 0 else False

    async def _download_pdf(self, url: str, output_path: Path) -> bool:
        """Download PDF from URL."""
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "parser/1.0"},
                )
                response.raise_for_status()

                content = response.content
                content_type = response.headers.get("content-type", "")

                # Verify it's a PDF
                if "pdf" not in content_type.lower() and not content.startswith(b"%PDF"):
                    return False

                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(content)
                return True

        except Exception:
            return False

    async def retrieve_batch(
        self,
        papers: list[dict[str, Any]],
        output_dir: Path | None = None,
        verbose: bool = True,
        save_progress: bool = True,
        max_concurrent: int = 1,
    ) -> list[RetrievalResult]:
        """Retrieve PDFs for multiple papers.

        Args:
            papers: List of dicts with 'doi' and/or 'title' keys
            output_dir: Override output directory
            verbose: Show progress
            save_progress: Save progress to file for resume
            max_concurrent: Maximum concurrent downloads (default 1 for rate limiting)

        Returns:
            List of RetrievalResult objects
        """
        out_dir = Path(output_dir) if output_dir else Path(self.config.download.get("output_dir", "./downloads"))
        out_dir.mkdir(parents=True, exist_ok=True)

        progress_file = out_dir / self.config.batch.get("progress_file", ".retrieval_progress.json")
        completed: set[str] = set()

        # Load existing progress
        if save_progress and progress_file.exists():
            try:
                with open(progress_file) as f:
                    progress_data = json.load(f)
                    completed = set(progress_data.get("completed", []))
                if verbose:
                    print(f"Resuming from {len(completed)} completed papers")
            except Exception:
                pass

        results = []
        total = len(papers)

        # Use semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        async def retrieve_one(idx: int, paper: dict) -> tuple[int, RetrievalResult]:
            async with semaphore:
                doi = paper.get("doi")
                title = paper.get("title", "")
                identifier = doi or title

                # Skip if already completed
                if identifier in completed:
                    if verbose:
                        print(f"[{idx}/{total}] Skipping (already done): {identifier[:50]}")
                    return idx, RetrievalResult(
                        doi=doi, title=title or "",
                        status=RetrievalStatus.SKIPPED,
                        pdf_path=None,
                    )

                if verbose:
                    print(f"\n[{idx}/{total}] Processing: {identifier[:60]}...")

                result = await self.retrieve(doi=doi, title=title, output_dir=out_dir, verbose=verbose)

                # Save progress
                if save_progress and result.status in (RetrievalStatus.SUCCESS, RetrievalStatus.SKIPPED):
                    completed.add(identifier)
                    try:
                        with open(progress_file, "w") as f:
                            json.dump({"completed": list(completed)}, f)
                    except Exception:
                        pass

                return idx, result

        if max_concurrent > 1:
            # Concurrent execution
            tasks = [retrieve_one(i, paper) for i, paper in enumerate(papers, 1)]
            task_results = await asyncio.gather(*tasks)
            # Sort by original index
            task_results.sort(key=lambda x: x[0])
            results = [r for _, r in task_results]
        else:
            # Sequential execution (original behavior)
            for i, paper in enumerate(papers, 1):
                _, result = await retrieve_one(i, paper)
                results.append(result)
                # Rate limit between papers
                await asyncio.sleep(self.config.rate_limits.get("global_delay", 1.0))

        return results
