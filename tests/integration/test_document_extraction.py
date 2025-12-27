"""Integration tests for document extraction."""


import pytest

from ingestor.extractors.text import TxtExtractor
from ingestor.types import MediaType


class TestTxtExtraction:
    """Integration tests for text file extraction."""

    @pytest.fixture
    def extractor(self):
        return TxtExtractor()

    @pytest.mark.asyncio
    async def test_extract_utf8_text(self, extractor, sample_txt):
        """Test extracting UTF-8 text file."""
        if not sample_txt.exists():
            pytest.skip("Fixture not generated")

        result = await extractor.extract(sample_txt)

        assert result.media_type == MediaType.TXT
        assert result.markdown  # Has content
        assert result.source == str(sample_txt)

    @pytest.mark.asyncio
    async def test_extract_latin1_text(self, extractor, sample_txt_latin1):
        """Test extracting Latin-1 encoded file."""
        if not sample_txt_latin1.exists():
            pytest.skip("Fixture not generated")

        result = await extractor.extract(sample_txt_latin1)

        assert result.media_type == MediaType.TXT
        assert result.charset  # Should detect encoding

    @pytest.mark.asyncio
    async def test_extract_markdown_file(self, extractor, sample_md):
        """Test extracting .md markdown file."""
        if not sample_md.exists():
            pytest.skip("Fixture not generated")

        result = await extractor.extract(sample_md)

        assert result.media_type == MediaType.TXT
        assert result.markdown
        assert "Markdown Document" in result.markdown

    @pytest.mark.asyncio
    async def test_extract_rst_file(self, extractor, sample_rst):
        """Test extracting .rst reStructuredText file."""
        if not sample_rst.exists():
            pytest.skip("Fixture not generated")

        result = await extractor.extract(sample_rst)

        assert result.media_type == MediaType.TXT
        assert result.markdown
        assert "RST Document" in result.markdown


class TestDocxExtraction:
    """Integration tests for DOCX extraction."""

    @pytest.fixture
    def extractor(self):
        try:
            from ingestor.extractors.docx import DocxExtractor
            return DocxExtractor()
        except ImportError:
            pytest.skip("docx dependencies not installed")

    @pytest.mark.asyncio
    async def test_extract_docx(self, extractor, sample_docx):
        """Test extracting DOCX file."""
        if not sample_docx.exists():
            pytest.skip("Fixture not generated")

        result = await extractor.extract(sample_docx)

        assert result.media_type == MediaType.DOCX
        assert result.markdown
        # Should contain heading from document
        assert "Test Document" in result.markdown or "Section" in result.markdown


class TestPptxExtraction:
    """Integration tests for PPTX extraction."""

    @pytest.fixture
    def extractor(self):
        try:
            from ingestor.extractors.pptx import PptxExtractor
            return PptxExtractor()
        except ImportError:
            pytest.skip("pptx dependencies not installed")

    @pytest.mark.asyncio
    async def test_extract_pptx(self, extractor, sample_pptx):
        """Test extracting PPTX file."""
        if not sample_pptx.exists():
            pytest.skip("Fixture not generated")

        result = await extractor.extract(sample_pptx)

        assert result.media_type == MediaType.PPTX
        assert result.markdown
        # Should have slide markers
        assert "Slide" in result.markdown or "Presentation" in result.markdown
