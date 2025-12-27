"""Paper downloader module.

Simple interface for downloading papers. Uses PaperRetriever internally.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Config
from .retriever import PaperRetriever, RetrievalStatus


@dataclass
class DownloadConfig:
    """Configuration for paper downloading."""

    email: str | None = None
    s2_api_key: str | None = None
    output_dir: Path | None = None
    skip_existing: bool = True
    generate_bibtex: bool = True
    extract_references: bool = True
    max_references: int = 50


@dataclass
class DownloadResult:
    """Result of downloading a paper."""

    success: bool
    identifier: str
    pdf_path: Path | None = None
    bibtex_path: Path | None = None
    references_path: Path | None = None
    metadata: dict[str, Any] | None = None
    error: str | None = None


class PaperDownloader:
    """Downloads scientific papers as PDFs.

    Simplified wrapper around PaperRetriever.
    For more control, use PaperRetriever directly.

    Example:
        >>> downloader = PaperDownloader()
        >>> result = await downloader.download("arXiv:2005.11401")
    """

    def __init__(self, config: DownloadConfig | None = None):
        self.config = config or DownloadConfig()
        self._retriever: PaperRetriever | None = None

    @property
    def retriever(self) -> PaperRetriever:
        """Get or create the underlying retriever."""
        if self._retriever is None:
            retriever_config = Config.load()
            if self.config.email:
                retriever_config.email = self.config.email
            if self.config.s2_api_key:
                retriever_config.api_keys["semantic_scholar"] = self.config.s2_api_key
            if self.config.output_dir:
                retriever_config.download["output_dir"] = str(self.config.output_dir)
            retriever_config.download["skip_existing"] = self.config.skip_existing
            self._retriever = PaperRetriever(retriever_config)
        return self._retriever

    @property
    def output_dir(self) -> Path:
        if self.config.output_dir:
            self.config.output_dir.mkdir(parents=True, exist_ok=True)
            return self.config.output_dir
        return Path(self.retriever.config.download.get("output_dir", "./downloads"))

    def supports(self, source: str | Path) -> bool:
        """Check if this downloader can handle the source."""
        from ..doi2bib.resolver import IdentifierType, resolve_identifier
        return resolve_identifier(str(source)).type != IdentifierType.UNKNOWN

    async def download(
        self,
        source: str | Path,
        output_dir: Path | None = None,
    ) -> DownloadResult:
        """Download a paper."""
        from ..doi2bib.resolver import resolve_identifier

        source_str = str(source)
        out_dir = Path(output_dir) if output_dir else self.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            identifier = resolve_identifier(source_str)

            result = await self.retriever.retrieve(
                doi=identifier.doi,
                title=identifier.value if not identifier.doi else None,
                output_dir=out_dir,
                verbose=False,
            )

            if result.status not in (RetrievalStatus.SUCCESS, RetrievalStatus.SKIPPED):
                return DownloadResult(
                    success=False,
                    identifier=source_str,
                    error=result.error or "Could not download PDF",
                )

            pdf_path = Path(result.pdf_path) if result.pdf_path else None

            # Generate BibTeX
            bibtex_path = None
            if self.config.generate_bibtex and result.metadata:
                bibtex_path = self._generate_bibtex(result.metadata, out_dir)

            # Get references
            references_path = None
            if self.config.extract_references:
                references_path = await self._get_references(identifier, out_dir)

            return DownloadResult(
                success=True,
                identifier=source_str,
                pdf_path=pdf_path,
                bibtex_path=bibtex_path,
                references_path=references_path,
                metadata=result.metadata,
            )
        except Exception as e:
            return DownloadResult(success=False, identifier=source_str, error=str(e))

    def _generate_bibtex(self, metadata: dict[str, Any], output_dir: Path) -> Path | None:
        """Generate BibTeX file from metadata."""
        from ..doi2bib.metadata import Author, PaperMetadata

        authors = [
            Author(name=a.get("name", ""), given=a.get("given"), family=a.get("family"))
            for a in metadata.get("authors", [])
        ]

        paper = PaperMetadata(
            title=metadata.get("title", ""),
            authors=authors,
            year=metadata.get("year"),
            doi=metadata.get("doi"),
            venue=metadata.get("venue"),
            publisher=metadata.get("publisher"),
        )

        bibtex_path = output_dir / "citation.bib"
        bibtex_path.write_text(paper.to_bibtex())
        return bibtex_path

    async def _get_references(self, identifier, output_dir: Path) -> Path | None:
        """Get references from Semantic Scholar."""
        from .clients import SemanticScholarClient

        s2 = SemanticScholarClient(api_key=self.config.s2_api_key)
        paper_id = identifier.doi or (f"ARXIV:{identifier.arxiv_id}" if identifier.arxiv_id else None)
        if not paper_id:
            return None

        try:
            refs = await s2.get_references(paper_id, limit=self.config.max_references)
            if not refs:
                return None

            lines = ["References", "=" * 40, ""]
            for i, ref in enumerate(refs, 1):
                authors = ", ".join(ref.get("authors", [])[:3])
                if len(ref.get("authors", [])) > 3:
                    authors += " et al."
                year = ref.get("year", "")
                lines.append(f"{i}. {authors} ({year}). {ref.get('title', 'Unknown')}.")

            refs_path = output_dir / "references.txt"
            refs_path.write_text("\n".join(lines))
            return refs_path
        except Exception:
            return None

    async def get_bibtex(self, source: str | Path) -> str | None:
        """Get BibTeX citation without downloading."""
        from ..doi2bib.metadata import get_metadata
        from ..doi2bib.resolver import resolve_identifier

        identifier = resolve_identifier(str(source))
        metadata = await get_metadata(identifier, email=self.config.email, s2_api_key=self.config.s2_api_key)
        return metadata.to_bibtex() if metadata else None

    async def get_metadata(self, source: str | Path) -> dict[str, Any] | None:
        """Get metadata without downloading."""
        from ..doi2bib.metadata import get_metadata
        from ..doi2bib.resolver import resolve_identifier

        identifier = resolve_identifier(str(source))
        metadata = await get_metadata(identifier, email=self.config.email, s2_api_key=self.config.s2_api_key)
        return metadata.to_dict() if metadata else None
