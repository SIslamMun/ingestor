"""Integration tests for EPUB extraction."""


import pytest

from ingestor.types import MediaType


class TestEpubExtraction:
    """Integration tests for EPUB ebook extraction."""

    @pytest.fixture
    def extractor(self):
        try:
            from ingestor.extractors.epub import EpubExtractor
            return EpubExtractor()
        except ImportError:
            pytest.skip("ebooklib not installed")

    def test_supports_epub(self, extractor):
        """Test supports .epub files."""
        assert extractor.supports("book.epub")
        assert extractor.supports("/path/to/book.epub")
        assert not extractor.supports("book.pdf")

    @pytest.mark.asyncio
    async def test_extract_epub(self, extractor, sample_epub):
        """Test extracting EPUB file."""
        if not sample_epub.exists():
            pytest.skip("EPUB fixture not available. Run: python -m tests.fixtures.generate_fixtures")

        result = await extractor.extract(sample_epub)

        assert result.media_type == MediaType.EPUB
        assert result.markdown
        # Should have content from our test ebook
        assert "Introduction" in result.markdown or "Chapter" in result.markdown

    @pytest.mark.asyncio
    async def test_epub_extracts_images(self, extractor, sample_epub):
        """Test EPUB image extraction."""
        if not sample_epub.exists():
            pytest.skip("EPUB fixture not available. Run: python -m tests.fixtures.generate_fixtures")

        result = await extractor.extract(sample_epub)

        # Images are extracted if present in EPUB
        # (our generated fixture doesn't have images)
        assert isinstance(result.images, list)

    @pytest.mark.asyncio
    async def test_epub_metadata(self, extractor, sample_epub):
        """Test EPUB metadata extraction."""
        if not sample_epub.exists():
            pytest.skip("EPUB fixture not available. Run: python -m tests.fixtures.generate_fixtures")

        result = await extractor.extract(sample_epub)

        assert "chapter_count" in result.metadata
        assert result.metadata["chapter_count"] >= 1
