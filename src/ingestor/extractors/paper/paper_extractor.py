"""Paper acquisition and extraction.

Main extractor that orchestrates:
1. Identifier resolution (DOI, arXiv, etc.)
2. Metadata retrieval from academic APIs
3. PDF download from open access sources
4. PDF extraction using Docling
5. Markdown generation with metadata header
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union
import asyncio

import httpx

from ..base import BaseExtractor
from ...types import ExtractionResult, MediaType


@dataclass
class PaperConfig:
    """Configuration for paper extraction."""
    
    # API credentials
    email: Optional[str] = None  # For CrossRef, Unpaywall, OpenAlex
    s2_api_key: Optional[str] = None  # Semantic Scholar API key
    
    # Download options
    download_dir: Optional[Path] = None  # Temp dir if None
    skip_existing: bool = True  # Skip if PDF already downloaded
    keep_pdf: bool = False  # Keep downloaded PDF in output directory
    
    # Extraction options
    extract_references: bool = False  # Extract citation list
    max_references: int = 50  # Max references to fetch
    generate_bibtex: bool = True  # Generate BibTeX file
    include_abstract: bool = True  # Include abstract in markdown
    
    # PDF extraction
    use_docling: bool = True  # Use Docling for PDF extraction
    extract_images: bool = True  # Extract images from PDF
    describe_images: bool = False  # Generate image descriptions with VLM


class PaperExtractor(BaseExtractor):
    """Extractor for scientific papers.
    
    Supports acquiring papers from:
    - DOI strings (e.g., 10.1234/example)
    - arXiv IDs (e.g., arXiv:2301.12345, 2301.12345)
    - Semantic Scholar IDs/URLs
    - OpenAlex IDs
    - Direct PDF URLs
    - Paper titles (search-based)
    
    Output includes:
    - Extracted markdown with metadata header
    - BibTeX citation file
    - Extracted images (optional)
    - Reference list (optional)
    """
    
    media_type = MediaType.PDF
    
    def __init__(self, config: Optional[PaperConfig] = None):
        """Initialize the paper extractor.
        
        Args:
            config: Paper extraction configuration
        """
        self.config = config or PaperConfig()
        self._temp_dir: Optional[Path] = None
    
    @property
    def download_dir(self) -> Path:
        """Get download directory."""
        if self.config.download_dir:
            self.config.download_dir.mkdir(parents=True, exist_ok=True)
            return self.config.download_dir
        
        if self._temp_dir is None:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="ingestor_paper_"))
        return self._temp_dir
    
    def supports(self, source: Union[str, Path]) -> bool:
        """Check if this extractor can handle the source.
        
        Args:
            source: DOI, arXiv ID, URL, or title
            
        Returns:
            True for paper identifiers
        """
        from .resolver import resolve_identifier, IdentifierType
        
        source_str = str(source)
        identifier = resolve_identifier(source_str)
        
        # We handle everything except UNKNOWN
        return identifier.type != IdentifierType.UNKNOWN
    
    async def extract(self, source: Union[str, Path]) -> ExtractionResult:
        """Extract content from a paper.
        
        Args:
            source: DOI, arXiv ID, URL, or title
            
        Returns:
            ExtractionResult with markdown, metadata, and images
        """
        from .resolver import resolve_identifier, IdentifierType
        from .metadata import get_metadata, PaperMetadata
        
        source_str = str(source)
        
        # Step 1: Resolve identifier
        identifier = resolve_identifier(source_str)
        
        # Step 2: Get metadata
        metadata = await get_metadata(
            identifier,
            email=self.config.email,
            s2_api_key=self.config.s2_api_key,
        )
        
        if not metadata:
            # Create minimal metadata from identifier
            metadata = PaperMetadata(
                title=f"Paper: {source_str}",
                doi=identifier.doi,
                arxiv_id=identifier.arxiv_id,
                pdf_url=identifier.url,
            )
        
        # Step 3: Get PDF URL
        pdf_url = await self._get_pdf_url(identifier, metadata)
        
        # Step 4: Download PDF
        pdf_path: Optional[Path] = None
        if pdf_url:
            pdf_path = await self._download_pdf(pdf_url, metadata)
        
        # Step 5: Extract PDF content
        extracted_content = ""
        images = []
        
        if pdf_path and pdf_path.exists():
            extracted_content, images = await self._extract_pdf(pdf_path)
        
        # Step 6: Build markdown output
        markdown = self._build_markdown(metadata, extracted_content)
        
        # Step 7: Get references if requested
        references_md = ""
        if self.config.extract_references:
            references_md = await self._get_references_markdown(identifier)
            if references_md:
                markdown += f"\n\n{references_md}"
        
        # Build result metadata
        result_metadata: dict[str, Any] = metadata.to_dict()
        result_metadata["identifier_type"] = identifier.type.value
        result_metadata["original_input"] = source_str
        
        if self.config.generate_bibtex:
            result_metadata["bibtex"] = metadata.to_bibtex()
        
        # Store PDF path if keeping it
        if self.config.keep_pdf and pdf_path and pdf_path.exists():
            result_metadata["pdf_path"] = str(pdf_path)
            result_metadata["_keep_pdf"] = True
        
        return ExtractionResult(
            markdown=markdown,
            title=metadata.title,
            source=source_str,
            media_type=MediaType.PDF,
            images=images,
            metadata=result_metadata,
        )
    
    async def _get_pdf_url(
        self,
        identifier: "PaperIdentifier",
        metadata: "PaperMetadata",
    ) -> Optional[str]:
        """Get PDF URL from various sources.
        
        Args:
            identifier: Resolved identifier
            metadata: Paper metadata
            
        Returns:
            PDF URL or None
        """
        from .resolver import IdentifierType
        
        # Check if we already have a PDF URL
        if metadata.pdf_url:
            return metadata.pdf_url
        
        if identifier.url and identifier.type == IdentifierType.PDF_URL:
            return identifier.url
        
        # Try arXiv for arXiv papers
        if identifier.arxiv_id or metadata.arxiv_id:
            arxiv_id = identifier.arxiv_id or metadata.arxiv_id
            return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        
        # Try Unpaywall for DOIs
        if (identifier.doi or metadata.doi) and self.config.email:
            from .clients import UnpaywallClient
            
            doi = identifier.doi or metadata.doi
            unpaywall = UnpaywallClient(email=self.config.email)
            pdf_url = await unpaywall.get_pdf_url(doi)
            if pdf_url:
                return pdf_url
        
        return None
    
    async def _download_pdf(
        self,
        pdf_url: str,
        metadata: "PaperMetadata",
    ) -> Optional[Path]:
        """Download PDF from URL.
        
        Args:
            pdf_url: URL to download
            metadata: Paper metadata for filename
            
        Returns:
            Path to downloaded PDF or None
        """
        # Generate filename
        safe_title = "".join(
            c if c.isalnum() or c in " -_" else "_"
            for c in (metadata.title or "paper")[:50]
        ).strip()
        
        if metadata.arxiv_id:
            filename = f"{metadata.arxiv_id.replace('/', '_')}.pdf"
        elif metadata.doi:
            filename = f"{metadata.doi.replace('/', '_')}.pdf"
        else:
            filename = f"{safe_title}.pdf"
        
        output_path = self.download_dir / filename
        
        # Check if already downloaded
        if self.config.skip_existing and output_path.exists():
            return output_path
        
        # Download
        async with httpx.AsyncClient(
            timeout=60,
            follow_redirects=True,
        ) as client:
            try:
                response = await client.get(
                    pdf_url,
                    headers={
                        "User-Agent": "ingestor/1.0 (https://github.com/shazzadhk/ingestor)",
                    },
                )
                response.raise_for_status()
                
                # Verify it's a PDF
                content_type = response.headers.get("content-type", "")
                content = response.content
                
                if "pdf" not in content_type.lower() and not content.startswith(b"%PDF"):
                    return None
                
                output_path.write_bytes(content)
                return output_path
                
            except Exception:
                return None
    
    async def _extract_pdf(
        self,
        pdf_path: Path,
    ) -> tuple[str, list]:
        """Extract content from PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (markdown_content, images)
        """
        try:
            # Try to use PDF extractor
            from ..pdf import PDFExtractor, PDFConfig
            
            config = PDFConfig(
                use_docling=self.config.use_docling,
                extract_images=self.config.extract_images,
            )
            extractor = PDFExtractor(config=config)
            result = await extractor.extract(pdf_path)
            
            return result.markdown, result.images
            
        except ImportError:
            # PDF extractor not available, try basic extraction
            return await self._basic_pdf_extract(pdf_path), []
        except Exception:
            return "", []
    
    async def _basic_pdf_extract(self, pdf_path: Path) -> str:
        """Basic PDF text extraction fallback.
        
        Args:
            pdf_path: Path to PDF
            
        Returns:
            Extracted text
        """
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(pdf_path)
            text_parts = []
            
            for page in doc:
                text = page.get_text()
                if text.strip():
                    text_parts.append(text)
            
            doc.close()
            return "\n\n".join(text_parts)
            
        except Exception:
            return ""
    
    def _build_markdown(
        self,
        metadata: "PaperMetadata",
        content: str,
    ) -> str:
        """Build markdown output with metadata header.
        
        Args:
            metadata: Paper metadata
            content: Extracted content
            
        Returns:
            Complete markdown document
        """
        parts = []
        
        # YAML frontmatter
        parts.append("---")
        parts.append(f"title: \"{metadata.title}\"")
        
        if metadata.authors:
            authors_str = ", ".join(a.name for a in metadata.authors)
            parts.append(f"authors: \"{authors_str}\"")
        
        if metadata.year:
            parts.append(f"year: {metadata.year}")
        
        if metadata.venue:
            parts.append(f"venue: \"{metadata.venue}\"")
        
        if metadata.doi:
            parts.append(f"doi: \"{metadata.doi}\"")
        
        if metadata.arxiv_id:
            parts.append(f"arxiv: \"{metadata.arxiv_id}\"")
        
        if metadata.citation_count is not None:
            parts.append(f"citations: {metadata.citation_count}")
        
        if metadata.pdf_url:
            parts.append(f"pdf_url: \"{metadata.pdf_url}\"")
        
        parts.append("---")
        parts.append("")
        
        # Title
        parts.append(f"# {metadata.title}")
        parts.append("")
        
        # Authors
        if metadata.authors:
            parts.append(f"**Authors:** {metadata.author_string}")
            parts.append("")
        
        # Publication info
        pub_info = []
        if metadata.venue:
            pub_info.append(metadata.venue)
        if metadata.year:
            pub_info.append(str(metadata.year))
        
        if pub_info:
            parts.append(f"**Published:** {', '.join(pub_info)}")
            parts.append("")
        
        # Links
        links = []
        if metadata.doi:
            links.append(f"[DOI](https://doi.org/{metadata.doi})")
        if metadata.arxiv_id:
            links.append(f"[arXiv](https://arxiv.org/abs/{metadata.arxiv_id})")
        if metadata.pdf_url:
            links.append(f"[PDF]({metadata.pdf_url})")
        
        if links:
            parts.append(f"**Links:** {' | '.join(links)}")
            parts.append("")
        
        # Abstract
        if self.config.include_abstract and metadata.abstract:
            parts.append("## Abstract")
            parts.append("")
            parts.append(metadata.abstract)
            parts.append("")
        
        # Horizontal rule before content
        if content.strip():
            parts.append("---")
            parts.append("")
            parts.append("## Content")
            parts.append("")
            parts.append(content)
        
        return "\n".join(parts)
    
    async def _get_references_markdown(
        self,
        identifier: "PaperIdentifier",
    ) -> str:
        """Get references as markdown.
        
        Args:
            identifier: Paper identifier
            
        Returns:
            Markdown formatted references
        """
        from .clients import SemanticScholarClient
        
        s2 = SemanticScholarClient(api_key=self.config.s2_api_key)
        
        # Determine best ID to use
        if identifier.doi:
            paper_id = identifier.doi
        elif identifier.arxiv_id:
            paper_id = f"ARXIV:{identifier.arxiv_id}"
        elif identifier.value:
            paper_id = identifier.value
        else:
            return ""
        
        references = await s2.get_references(
            paper_id,
            limit=self.config.max_references,
        )
        
        if not references:
            return ""
        
        parts = ["## References", ""]
        
        for i, ref in enumerate(references, 1):
            title = ref.get("title", "Unknown")
            authors = ref.get("authors", [])
            year = ref.get("year", "")
            doi = ref.get("doi")
            
            author_str = ", ".join(authors[:3])
            if len(authors) > 3:
                author_str += " et al."
            
            entry = f"{i}. {author_str}"
            if year:
                entry += f" ({year})."
            entry += f" *{title}*."
            
            if doi:
                entry += f" [DOI](https://doi.org/{doi})"
            
            parts.append(entry)
        
        return "\n".join(parts)
    
    async def get_bibtex(self, source: Union[str, Path]) -> Optional[str]:
        """Get BibTeX citation for a paper.
        
        Args:
            source: DOI, arXiv ID, or other identifier
            
        Returns:
            BibTeX string or None
        """
        from .resolver import resolve_identifier
        from .metadata import get_metadata
        
        identifier = resolve_identifier(str(source))
        metadata = await get_metadata(
            identifier,
            email=self.config.email,
            s2_api_key=self.config.s2_api_key,
        )
        
        if metadata:
            return metadata.to_bibtex()
        return None
    
    async def get_metadata(self, source: Union[str, Path]) -> Optional[dict[str, Any]]:
        """Get metadata for a paper without downloading.
        
        Args:
            source: DOI, arXiv ID, or other identifier
            
        Returns:
            Metadata dict or None
        """
        from .resolver import resolve_identifier
        from .metadata import get_metadata
        
        identifier = resolve_identifier(str(source))
        metadata = await get_metadata(
            identifier,
            email=self.config.email,
            s2_api_key=self.config.s2_api_key,
        )
        
        if metadata:
            return metadata.to_dict()
        return None
