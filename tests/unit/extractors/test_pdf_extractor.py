"""Unit tests for PDF extractor."""

from unittest.mock import MagicMock, patch

import pytest

from ingestor.extractors.pdf import (
    DoclingNotInstalledError,
    PdfConfig,
    PdfExtractor,
    PyMuPDFNotInstalledError,
)
from ingestor.types import MediaType


class TestPdfConfig:
    """Tests for PdfConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = PdfConfig()

        assert config.images_scale == 2.0
        assert config.generate_pictures is True
        assert config.min_image_width == 200
        assert config.min_image_height == 150
        assert config.min_image_area == 40000
        assert config.use_postprocess is True
        assert config.use_ocr_fallback is True
        assert config.extract_tables is True
        assert config.extract_equations is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = PdfConfig(
            images_scale=3.0,
            generate_pictures=False,
            min_image_width=100,
            use_postprocess=False,
        )

        assert config.images_scale == 3.0
        assert config.generate_pictures is False
        assert config.min_image_width == 100
        assert config.use_postprocess is False


class TestPdfExtractor:
    """Tests for PdfExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create a PdfExtractor instance."""
        return PdfExtractor()

    @pytest.fixture
    def extractor_with_config(self):
        """Create a PdfExtractor with custom config."""
        config = PdfConfig(
            use_postprocess=False,
            use_ocr_fallback=False,
        )
        return PdfExtractor(config=config)

    def test_media_type(self, extractor):
        """Test media_type is PDF."""
        assert extractor.media_type == MediaType.PDF

    def test_supports_pdf_file(self, extractor):
        """Test supports returns True for PDF files."""
        assert extractor.supports("document.pdf") is True
        assert extractor.supports("path/to/paper.PDF") is True
        assert extractor.supports("/absolute/path/file.pdf") is True

    def test_not_supports_other_files(self, extractor):
        """Test supports returns False for non-PDF files."""
        assert extractor.supports("document.docx") is False
        assert extractor.supports("image.png") is False
        assert extractor.supports("text.txt") is False

    def test_custom_config(self, extractor_with_config):
        """Test extractor uses custom config."""
        assert extractor_with_config.config.use_postprocess is False
        assert extractor_with_config.config.use_ocr_fallback is False

    @pytest.mark.asyncio
    async def test_extract_nonexistent_file(self, extractor):
        """Test extracting non-existent file returns error."""
        result = await extractor.extract("/nonexistent/path/file.pdf")

        assert result.media_type == MediaType.PDF
        assert "Error" in result.markdown
        assert "not found" in result.markdown.lower() or "error" in result.metadata.get("status", "")

    @pytest.mark.asyncio
    async def test_extract_returns_extraction_result(self, extractor, tmp_path):
        """Test extract returns ExtractionResult."""
        # Create a dummy PDF file (won't work without Docling)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        # Without Docling/PyMuPDF installed, should return error result
        result = await extractor.extract(pdf_file)

        assert result is not None
        assert result.media_type == MediaType.PDF
        assert result.source == str(pdf_file)


class TestDoclingNotInstalledError:
    """Tests for DoclingNotInstalledError."""

    def test_error_message(self):
        """Test error message content."""
        error = DoclingNotInstalledError()
        assert "Docling is not installed" in str(error)
        assert "uv sync --extra pdf" in str(error)


class TestPyMuPDFNotInstalledError:
    """Tests for PyMuPDFNotInstalledError."""

    def test_error_message(self):
        """Test error message content."""
        error = PyMuPDFNotInstalledError()
        assert "PyMuPDF is not installed" in str(error)
        assert "uv sync --extra pdf" in str(error)


class TestPdfExtractorWithMocks:
    """Tests for PdfExtractor with mocked dependencies."""

    @pytest.fixture
    def extractor(self):
        """Create a PdfExtractor instance."""
        return PdfExtractor()

    @pytest.mark.asyncio
    async def test_docling_extraction_called(self, extractor, tmp_path):
        """Test that Docling extraction is attempted first."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        with patch.object(extractor, "_extract_with_docling") as mock_docling:
            mock_result = MagicMock()
            mock_result.markdown = "# Test"
            mock_result.images = []
            mock_docling.return_value = mock_result

            await extractor.extract(pdf_file)

            mock_docling.assert_called_once_with(pdf_file)

    @pytest.mark.asyncio
    async def test_pymupdf_fallback_on_docling_error(self, extractor, tmp_path):
        """Test PyMuPDF fallback when Docling fails."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        with patch.object(extractor, "_extract_with_docling") as mock_docling:
            mock_docling.side_effect = DoclingNotInstalledError()

            with patch.object(extractor, "_extract_with_pymupdf") as mock_pymupdf:
                mock_result = MagicMock()
                mock_result.markdown = "# Fallback"
                mock_result.images = []
                mock_pymupdf.return_value = mock_result

                await extractor.extract(pdf_file)

                mock_pymupdf.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_fallback_when_disabled(self, tmp_path):
        """Test no fallback when use_ocr_fallback is False."""
        config = PdfConfig(use_ocr_fallback=False)
        extractor = PdfExtractor(config=config)

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        with patch.object(extractor, "_extract_with_docling") as mock_docling:
            mock_docling.side_effect = DoclingNotInstalledError()

            result = await extractor.extract(pdf_file)

            # Should return error result, not call PyMuPDF
            assert "error" in result.metadata.get("status", "")
