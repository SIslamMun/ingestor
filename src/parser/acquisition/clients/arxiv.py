"""arXiv API client for preprint access."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

import httpx

from .base import BaseClient, RateLimiter


class ArxivClient(BaseClient):
    """Client for the arXiv API.

    See: https://info.arxiv.org/help/api/
    """

    BASE_URL = "https://export.arxiv.org/api"
    PDF_BASE_URL = "https://arxiv.org/pdf"
    ABS_BASE_URL = "https://arxiv.org/abs"

    # arXiv ID patterns
    NEW_ID_PATTERN = re.compile(r"^(\d{4}\.\d{4,5})(v\d+)?$")  # 2301.12345
    OLD_ID_PATTERN = re.compile(r"^([a-z-]+/\d{7})(v\d+)?$")  # hep-th/9901001

    def __init__(self):
        """Initialize the arXiv client."""
        # arXiv: ~1 request per 3 seconds recommended
        super().__init__(
            base_url=self.BASE_URL,
            rate_limiter=RateLimiter(calls_per_second=0.33),
        )

    def normalize_id(self, arxiv_id: str) -> str:
        """Normalize an arXiv ID.

        Args:
            arxiv_id: arXiv ID in various formats

        Returns:
            Normalized arXiv ID (without version suffix)
        """
        arxiv_id = arxiv_id.strip()

        # Remove URL prefix
        if "arxiv.org" in arxiv_id:
            arxiv_id = re.sub(r"^https?://arxiv\.org/(?:abs|pdf)/", "", arxiv_id)

        # Remove arXiv: prefix
        if arxiv_id.lower().startswith("arxiv:"):
            arxiv_id = arxiv_id[6:]

        # Remove .pdf suffix
        arxiv_id = re.sub(r"\.pdf$", "", arxiv_id, flags=re.IGNORECASE)

        return arxiv_id

    async def get_paper_metadata(self, identifier: str) -> dict[str, Any] | None:
        """Get paper metadata from arXiv.

        Args:
            identifier: arXiv ID

        Returns:
            Paper metadata dict or None
        """
        arxiv_id = self.normalize_id(identifier)

        await self.rate_limiter.wait()

        # Use the Atom API
        url = f"{self.BASE_URL}/query"
        params: dict[str, str | int] = {
            "id_list": arxiv_id,
            "max_results": 1,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()

                # Parse Atom XML response
                return self._parse_atom_entry(response.text, arxiv_id)

            except Exception:
                return None

    def _parse_atom_entry(self, xml_text: str, arxiv_id: str) -> dict[str, Any] | None:
        """Parse arXiv Atom API response."""
        import xml.etree.ElementTree as ET

        # Define namespaces
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        try:
            root = ET.fromstring(xml_text)

            # Find the entry
            entry = root.find("atom:entry", ns)
            if entry is None:
                return None

            # Check for error
            title_elem = entry.find("atom:title", ns)
            if title_elem is not None and "Error" in (title_elem.text or ""):
                return None

            # Extract authors
            authors = []
            for author in entry.findall("atom:author", ns):
                name_elem = author.find("atom:name", ns)
                if name_elem is not None and name_elem.text:
                    authors.append({"name": name_elem.text.strip()})

            # Extract categories
            categories = []
            for cat in entry.findall("arxiv:primary_category", ns):
                term = cat.get("term")
                if term:
                    categories.append(term)
            for cat in entry.findall("atom:category", ns):
                term = cat.get("term")
                if term and term not in categories:
                    categories.append(term)

            # Get title
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else None
            # Clean up newlines in title
            if title:
                title = " ".join(title.split())

            # Get abstract
            summary_elem = entry.find("atom:summary", ns)
            abstract = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else None
            if abstract:
                abstract = " ".join(abstract.split())

            # Get published date
            published_elem = entry.find("atom:published", ns)
            published = published_elem.text if published_elem is not None else None

            # Extract year from published date
            year = None
            if published:
                match = re.match(r"(\d{4})", published)
                if match:
                    year = int(match.group(1))

            # Get DOI if linked
            doi = None
            for link in entry.findall("atom:link", ns):
                href = link.get("href", "")
                if "doi.org" in href:
                    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", href)
                    break

            # Also check arxiv:doi element
            if not doi:
                doi_elem = entry.find("arxiv:doi", ns)
                if doi_elem is not None and doi_elem.text:
                    doi = doi_elem.text.strip()

            return {
                "title": title,
                "authors": authors,
                "year": year,
                "abstract": abstract,
                "arxiv_id": arxiv_id,
                "doi": doi or f"10.48550/arXiv.{arxiv_id}",
                "pdf_url": f"{self.PDF_BASE_URL}/{arxiv_id}.pdf",
                "abs_url": f"{self.ABS_BASE_URL}/{arxiv_id}",
                "categories": categories,
                "primary_category": categories[0] if categories else None,
                "published": published,
                "source": "arxiv",
            }

        except ET.ParseError:
            return None

    async def search(
        self,
        query: str,
        limit: int = 10,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search arXiv for papers.

        Args:
            query: Search query (title, author, abstract)
            limit: Maximum results
            category: Filter by arXiv category (e.g., "cs.CL")

        Returns:
            List of paper metadata
        """
        await self.rate_limiter.wait()

        # Build search query
        search_query = f"all:{query}"
        if category:
            search_query = f"({search_query}) AND cat:{category}"

        url = f"{self.BASE_URL}/query"
        params: dict[str, str | int] = {
            "search_query": search_query,
            "max_results": min(limit, 100),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()

                return self._parse_atom_feed(response.text)

            except Exception:
                return []

    def _parse_atom_feed(self, xml_text: str) -> list[dict[str, Any]]:
        """Parse arXiv Atom feed with multiple entries."""
        import xml.etree.ElementTree as ET

        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        results = []

        try:
            root = ET.fromstring(xml_text)

            for entry in root.findall("atom:entry", ns):
                # Get ID
                id_elem = entry.find("atom:id", ns)
                if id_elem is None or not id_elem.text:
                    continue

                # Extract arXiv ID from URL
                arxiv_id = id_elem.text.split("/")[-1]

                # Get title
                title_elem = entry.find("atom:title", ns)
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else None
                if title:
                    title = " ".join(title.split())

                # Get authors
                authors = []
                for author in entry.findall("atom:author", ns):
                    name_elem = author.find("atom:name", ns)
                    if name_elem is not None and name_elem.text:
                        authors.append(name_elem.text.strip())

                # Get published date
                published_elem = entry.find("atom:published", ns)
                published = published_elem.text if published_elem is not None else None

                year = None
                if published:
                    match = re.match(r"(\d{4})", published)
                    if match:
                        year = int(match.group(1))

                results.append({
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "arxiv_id": arxiv_id,
                    "doi": f"10.48550/arXiv.{arxiv_id}",
                    "pdf_url": f"{self.PDF_BASE_URL}/{arxiv_id}.pdf",
                })

        except ET.ParseError:
            pass

        return results

    async def download_pdf(
        self,
        arxiv_id: str,
        output_dir: Path | None = None,
    ) -> Path | None:
        """Download PDF for an arXiv paper.

        Args:
            arxiv_id: arXiv ID
            output_dir: Directory to save PDF (uses temp dir if None)

        Returns:
            Path to downloaded PDF or None
        """
        arxiv_id = self.normalize_id(arxiv_id)
        pdf_url = f"{self.PDF_BASE_URL}/{arxiv_id}.pdf"

        if output_dir is None:
            output_dir = Path(tempfile.gettempdir())

        output_path = output_dir / f"{arxiv_id.replace('/', '_')}.pdf"

        await self.rate_limiter.wait()

        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            try:
                response = await client.get(pdf_url)
                response.raise_for_status()

                # Verify it's a PDF
                content_type = response.headers.get("content-type", "")
                if "pdf" not in content_type.lower() and not response.content.startswith(b"%PDF"):
                    return None

                output_path.write_bytes(response.content)
                return output_path

            except Exception:
                return None

    def get_pdf_url(self, arxiv_id: str) -> str:
        """Get direct PDF URL for an arXiv paper.

        Args:
            arxiv_id: arXiv ID

        Returns:
            PDF URL
        """
        arxiv_id = self.normalize_id(arxiv_id)
        return f"{self.PDF_BASE_URL}/{arxiv_id}.pdf"
