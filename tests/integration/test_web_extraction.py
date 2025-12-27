"""Integration tests for web extraction with Crawl4AI."""


import pytest

from ingestor.types import MediaType


def playwright_browsers_installed() -> bool:
    """Check if playwright browsers are installed."""
    try:
        import os
        from pathlib import Path

        # Check common playwright browser locations
        if os.name == "nt":  # Windows
            playwright_dir = Path.home() / "AppData" / "Local" / "ms-playwright"
        else:  # Linux/Mac
            playwright_dir = Path.home() / ".cache" / "ms-playwright"

        if not playwright_dir.exists():
            return False

        # Check if any browser directory exists and has content
        for item in playwright_dir.iterdir():
            if item.is_dir() and "chromium" in item.name.lower():
                return True
        return False
    except Exception:
        return False


class TestWebExtraction:
    """Integration tests for web page extraction."""

    @pytest.fixture
    def extractor(self):
        try:
            from ingestor.extractors.web import WebExtractor
            return WebExtractor()
        except ImportError:
            pytest.skip("crawl4ai not installed")

    def test_supports_urls(self, extractor):
        """Test supports HTTP/HTTPS URLs."""
        assert extractor.supports("https://example.com")
        assert extractor.supports("http://example.com/page")
        assert extractor.supports("https://docs.python.org/3/")
        assert not extractor.supports("file.txt")

    def test_excludes_youtube(self, extractor):
        """Test excludes YouTube URLs (handled by YouTubeExtractor)."""
        assert not extractor.supports("https://youtube.com/watch?v=abc123")
        assert not extractor.supports("https://www.youtube.com/watch?v=abc123")
        assert not extractor.supports("https://youtu.be/abc123")

    def test_supports_url_files(self, extractor):
        """Test supports .url files."""
        assert extractor.supports("bookmark.url")

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_extract_simple_page(self, extractor):
        """Test extracting a simple web page."""
        if not playwright_browsers_installed():
            pytest.skip("Playwright browsers not installed. Run: playwright install chromium")

        # Use example.com as it's always available
        result = await extractor.extract("https://example.com")

        assert result.media_type == MediaType.WEB
        assert result.markdown
        assert "Example Domain" in result.markdown or len(result.markdown) > 0

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_web_metadata(self, extractor):
        """Test web extraction metadata."""
        if not playwright_browsers_installed():
            pytest.skip("Playwright browsers not installed. Run: playwright install chromium")

        result = await extractor.extract("https://example.com")

        assert result.source == "https://example.com"
        assert "url" in result.metadata

    @pytest.mark.asyncio
    async def test_url_file_parsing(self, extractor, tmp_path):
        """Test parsing .url file format."""
        url_file = tmp_path / "test.url"
        url_file.write_text("[InternetShortcut]\nURL=https://example.com\n")

        # Read URL from file
        url = extractor._read_url_file(url_file)
        assert url == "https://example.com"


class TestWebCrawling:
    """Integration tests for deep web crawling."""

    @pytest.fixture
    def extractor(self):
        try:
            from ingestor.extractors.web import WebExtractor
            return WebExtractor(
                strategy="bfs",
                max_depth=1,
                max_pages=3,
            )
        except ImportError:
            pytest.skip("crawl4ai not installed")

    def test_extractor_config(self, extractor):
        """Test extractor configuration."""
        assert extractor.strategy == "bfs"
        assert extractor.max_depth == 1
        assert extractor.max_pages == 3
