"""PDF extractor using Docling for ML-based extraction.

Supports:
- Text extraction with structure preservation
- Image/figure extraction
- Multi-column layout handling
- Academic paper features (citations, references)
- Table extraction
- LaTeX equation handling (via Docling)
- OCR fallback for scanned PDFs (via PyMuPDF)
- PDF URLs (automatically downloaded)
"""

from __future__ import annotations

import asyncio
import io
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from ...types import ExtractedImage, ExtractionResult, MediaType
from ..base import BaseExtractor

if TYPE_CHECKING:
    pass


class DoclingNotInstalledError(ImportError):
    """Raised when Docling is not installed."""

    def __init__(self) -> None:
        super().__init__(
            "Docling is not installed. Install with: uv sync --extra pdf\n"
            "Note: Docling requires ~500MB for ML models on first use."
        )


class PyMuPDFNotInstalledError(ImportError):
    """Raised when PyMuPDF is not installed."""

    def __init__(self) -> None:
        super().__init__(
            "PyMuPDF is not installed. Install with: uv sync --extra pdf"
        )


@dataclass
class PdfConfig:
    """Configuration for PDF extraction.

    Attributes:
        images_scale: Resolution multiplier for extracted images (default: 2.0)
        generate_pictures: Whether to extract figure images (default: True)
        min_image_width: Minimum image width in pixels to keep (default: 200)
        min_image_height: Minimum image height in pixels to keep (default: 150)
        min_image_area: Minimum image area in pixels to keep (default: 40000)
        use_postprocess: Apply academic paper post-processing (default: True)
        use_ocr_fallback: Fall back to OCR for scanned PDFs (default: True)
        extract_tables: Extract tables as markdown (default: True)
        extract_equations: Extract LaTeX equations (default: True)
    """

    images_scale: float = 2.0
    generate_pictures: bool = True
    min_image_width: int = 200
    min_image_height: int = 150
    min_image_area: int = 40000
    use_postprocess: bool = True
    use_ocr_fallback: bool = True
    extract_tables: bool = True
    extract_equations: bool = True


class PdfExtractor(BaseExtractor):
    """Extract content from PDF files using Docling.

    Features:
    - ML-based structure recognition (Docling)
    - Multi-column layout handling
    - Figure/image extraction with filtering
    - Academic paper support (citations, references)
    - Table extraction
    - OCR fallback for scanned documents

    Example:
        >>> extractor = PdfExtractor()
        >>> result = await extractor.extract("paper.pdf")
        >>> print(result.markdown)
    """

    media_type = MediaType.PDF

    def __init__(self, config: PdfConfig | None = None) -> None:
        """Initialize PDF extractor.

        Args:
            config: Extraction configuration options
        """
        self.config = config or PdfConfig()
        self._docling_available: bool | None = None
        self._pymupdf_available: bool | None = None

    def supports(self, source: str | Path) -> bool:
        """Check if this extractor handles the source.

        Args:
            source: Path or URL to check

        Returns:
            True if this is a PDF file or PDF URL
        """
        source_str = str(source).lower()
        # Check for PDF URLs
        if source_str.startswith(("http://", "https://")):
            # Remove query string and fragment for extension check
            url_path = source_str.split("?")[0].split("#")[0]
            return url_path.endswith(".pdf")
        return source_str.endswith(".pdf")

    def _is_url(self, source: str | Path) -> bool:
        """Check if source is a URL."""
        return str(source).startswith(("http://", "https://"))

    async def _download_pdf(self, url: str) -> Path:
        """Download PDF from URL to a temporary file.

        Args:
            url: URL to download

        Returns:
            Path to temporary PDF file
        """
        import httpx

        # Extract filename from URL
        parsed = urlparse(url)
        path_part = parsed.path.split("?")[0].split("#")[0]
        filename = Path(path_part).name or "downloaded.pdf"
        if not filename.endswith(".pdf"):
            filename = filename + ".pdf"

        # Download to temp file
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Create temp file
            temp_dir = Path(tempfile.mkdtemp())
            temp_path = temp_dir / filename

            temp_path.write_bytes(response.content)
            return temp_path

    async def extract(self, source: str | Path) -> ExtractionResult:
        """Extract content from a PDF file or URL.

        Uses Docling for ML-based extraction with optional post-processing
        for academic papers. Falls back to PyMuPDF OCR for scanned documents.

        Args:
            source: Path to the PDF file or URL to a PDF

        Returns:
            ExtractionResult containing markdown, images, and metadata
        """
        # Handle PDF URLs
        temp_path: Path | None = None
        original_source = str(source)

        if self._is_url(source):
            try:
                temp_path = await self._download_pdf(str(source))
                path = temp_path
            except Exception as e:
                return self._error_result(
                    Path(urlparse(str(source)).path.split("/")[-1] or "pdf"),
                    f"Failed to download PDF from {source}: {e}"
                )
        else:
            path = Path(source)

        if not path.exists():
            return self._error_result(path, f"File not found: {path}")

        try:
            # Try Docling extraction first
            try:
                result = await self._extract_with_docling(path)
            except DoclingNotInstalledError:
                # Fall back to PyMuPDF if Docling not available
                if self.config.use_ocr_fallback:
                    try:
                        result = await self._extract_with_pymupdf(path)
                    except PyMuPDFNotInstalledError:
                        return self._error_result(
                            path,
                            "PDF extraction requires either Docling or PyMuPDF.\n"
                            "Install with: uv sync --extra pdf"
                        )
                else:
                    return self._error_result(
                        path,
                        "Docling is not installed. Install with: uv sync --extra pdf"
                    )
            except Exception as e:
                # Try OCR fallback on extraction errors
                if self.config.use_ocr_fallback:
                    try:
                        result = await self._extract_with_pymupdf(path)
                    except Exception:
                        pass
                    else:
                        # Add source URL to metadata if downloaded
                        if temp_path and self._is_url(original_source):
                            result.metadata["source_url"] = original_source
                        return result
                return self._error_result(path, f"Extraction failed: {e}")

            # Add source URL to metadata if downloaded
            if temp_path and self._is_url(original_source):
                result.metadata["source_url"] = original_source

            return result

        finally:
            # Clean up temp file
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                    temp_path.parent.rmdir()
                except Exception:
                    pass

    async def _extract_with_docling(self, path: Path) -> ExtractionResult:
        """Extract PDF content using Docling ML pipeline.

        Args:
            path: Path to PDF file

        Returns:
            ExtractionResult with markdown and images
        """
        try:
            import docling  # noqa: F401
        except ImportError as e:
            raise DoclingNotInstalledError() from e

        # Run Docling in thread pool (it's CPU-bound)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._run_docling_extraction,
            path,
        )

        return result

    def _run_docling_extraction(self, path: Path) -> ExtractionResult:
        """Synchronous Docling extraction (runs in executor).

        Args:
            path: Path to PDF file

        Returns:
            ExtractionResult with markdown and images
        """
        from docling.datamodel.base_models import ConversionStatus, InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        # Configure Docling pipeline
        pipeline_options = PdfPipelineOptions()
        pipeline_options.images_scale = self.config.images_scale
        pipeline_options.generate_picture_images = self.config.generate_pictures
        pipeline_options.do_formula_enrichment = self.config.extract_equations

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        # Run conversion
        result = converter.convert(str(path))

        if result.status not in [ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS]:
            errors = getattr(result, "errors", [])
            error_msg = "; ".join(str(e) for e in errors) if errors else "Unknown error"
            raise RuntimeError(f"Docling conversion failed ({result.status}): {error_msg}")

        # Extract images (filtering out small logos/badges)
        images: list[ExtractedImage] = []
        figure_num = 1

        if self.config.generate_pictures and hasattr(result.document, "pictures"):
            for picture in result.document.pictures:
                try:
                    pil_image = picture.get_image(result.document)
                    if pil_image is not None:
                        # Filter by dimensions
                        width, height = pil_image.size
                        area = width * height

                        if (width < self.config.min_image_width or
                            height < self.config.min_image_height or
                            area < self.config.min_image_area):
                            continue

                        # Convert to bytes
                        img_buffer = io.BytesIO()
                        pil_image.save(img_buffer, format="PNG")
                        img_data = img_buffer.getvalue()

                        # Get page number if available
                        page_num = getattr(picture, "page_no", None)

                        images.append(ExtractedImage(
                            filename=f"figure{figure_num}.png",
                            data=img_data,
                            format="png",
                            page=page_num,
                        ))
                        figure_num += 1
                except Exception:
                    pass  # Skip images that fail to extract

        # Export markdown
        markdown = result.document.export_to_markdown()

        # Apply post-processing for academic papers
        if self.config.use_postprocess:
            from .postprocess import process_markdown
            image_filenames = [img.filename for img in images]
            markdown = process_markdown(markdown, image_filenames)

        # Build metadata
        metadata = {
            "extractor": "docling",
            "image_count": len(images),
            "page_count": getattr(result.document, "page_count", None),
        }

        # Extract title from document if available
        title = path.stem
        if hasattr(result.document, "title") and result.document.title:
            title = result.document.title

        return ExtractionResult(
            markdown=markdown,
            title=title,
            source=str(path),
            media_type=MediaType.PDF,
            images=images,
            metadata=metadata,
        )

    async def _extract_with_pymupdf(self, path: Path) -> ExtractionResult:
        """Extract PDF content using PyMuPDF (fallback/OCR).

        Args:
            path: Path to PDF file

        Returns:
            ExtractionResult with markdown and images
        """
        try:
            import fitz  # noqa: F401 - PyMuPDF
        except ImportError as e:
            raise PyMuPDFNotInstalledError() from e

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._run_pymupdf_extraction,
            path,
        )

        return result

    def _run_pymupdf_extraction(self, path: Path) -> ExtractionResult:
        """Synchronous PyMuPDF extraction (runs in executor).

        Args:
            path: Path to PDF file

        Returns:
            ExtractionResult with markdown and images
        """
        import fitz

        doc = fitz.open(str(path))
        markdown_parts: list[str] = []
        images: list[ExtractedImage] = []
        figure_num = 1

        # Add title
        title = path.stem
        if doc.metadata and doc.metadata.get("title"):
            title = doc.metadata["title"]

        markdown_parts.append(f"# {title}\n")

        page_count = len(doc)

        # Extract text and images from each page
        for page_num, page in enumerate(doc, start=1):
            # Extract text
            text = page.get_text("text")
            if text.strip():
                markdown_parts.append(text)
                markdown_parts.append("\n")

            # Extract images
            if self.config.generate_pictures:
                for img in page.get_images():
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_data = base_image["image"]

                        # Check dimensions via PIL
                        from PIL import Image
                        pil_img = Image.open(io.BytesIO(image_data))
                        width, height = pil_img.size
                        area = width * height

                        if (width < self.config.min_image_width or
                            height < self.config.min_image_height or
                            area < self.config.min_image_area):
                            continue

                        # Convert to PNG
                        img_buffer = io.BytesIO()
                        pil_img.save(img_buffer, format="PNG")

                        images.append(ExtractedImage(
                            filename=f"figure{figure_num}.png",
                            data=img_buffer.getvalue(),
                            format="png",
                            page=page_num,
                        ))
                        figure_num += 1
                    except Exception:
                        pass

        doc.close()

        # Join all parts
        markdown = "\n".join(markdown_parts)

        # Apply basic cleanup (not full postprocess for OCR fallback)
        from .postprocess.cleanup import cleanup_text
        markdown = cleanup_text(markdown)

        metadata = {
            "extractor": "pymupdf",
            "image_count": len(images),
            "page_count": page_count,
            "note": "Fallback extraction - may have reduced structure quality",
        }

        return ExtractionResult(
            markdown=markdown,
            title=title,
            source=str(path),
            media_type=MediaType.PDF,
            images=images,
            metadata=metadata,
        )

    def _error_result(self, path: Path, message: str) -> ExtractionResult:
        """Create an error result.

        Args:
            path: Source file path
            message: Error message

        Returns:
            ExtractionResult with error information
        """
        markdown = f"""# PDF: {path.name}

> **Error:** {message}

**Source:** {path}
"""
        return ExtractionResult(
            markdown=markdown,
            title=path.stem,
            source=str(path),
            media_type=MediaType.PDF,
            images=[],
            metadata={
                "status": "error",
                "error": message,
            },
        )
