"""Real unit tests for Web extractor - no mocking."""

import pytest
from pathlib import Path

from ingestor.extractors.web.web_extractor import WebExtractor
from ingestor.types import MediaType


class TestWebExtractorInit:
    """Tests for WebExtractor initialization."""

    def test_default_init(self):
        """Test default initialization."""
        extractor = WebExtractor()
        
        assert extractor.strategy == "bfs"
        assert extractor.max_depth == 2
        assert extractor.max_pages == 50
        assert extractor.include_patterns == []
        assert extractor.exclude_patterns == []
        assert extractor.same_domain is True

    def test_custom_init(self):
        """Test custom initialization."""
        extractor = WebExtractor(
            strategy="dfs",
            max_depth=5,
            max_pages=100,
            include_patterns=["*/docs/*"],
            exclude_patterns=["*/login/*"],
            same_domain=False,
        )
        
        assert extractor.strategy == "dfs"
        assert extractor.max_depth == 5
        assert extractor.max_pages == 100
        assert extractor.include_patterns == ["*/docs/*"]
        assert extractor.exclude_patterns == ["*/login/*"]
        assert extractor.same_domain is False

    def test_media_type(self):
        """Test media type is WEB."""
        extractor = WebExtractor()
        assert extractor.media_type == MediaType.WEB


class TestWebExtractorCanExtract:
    """Tests for supports method."""

    @pytest.fixture
    def extractor(self):
        return WebExtractor()

    def test_supports_http_url(self, extractor):
        """Test supports for HTTP URLs."""
        assert extractor.supports("http://example.com")
        assert extractor.supports("http://example.com/page")
        assert extractor.supports("http://sub.example.com/page.html")

    def test_supports_https_url(self, extractor):
        """Test supports for HTTPS URLs."""
        assert extractor.supports("https://example.com")
        assert extractor.supports("https://example.com/page")
        assert extractor.supports("https://docs.python.org/3/tutorial/")

    def test_does_not_support_youtube_url(self, extractor):
        """Test supports returns False for YouTube URLs."""
        assert not extractor.supports("https://www.youtube.com/watch?v=abc123")
        assert not extractor.supports("https://youtu.be/abc123")

    def test_does_not_support_non_web_url(self, extractor):
        """Test supports returns False for non-web URLs."""
        assert not extractor.supports("ftp://example.com")
        assert not extractor.supports("file:///path/to/file")

    def test_does_not_support_local_file(self, extractor, tmp_path):
        """Test supports returns False for local files."""
        test_file = tmp_path / "test.html"
        test_file.write_text("<html></html>")
        
        assert not extractor.supports(str(test_file))

    def test_supports_url_file(self, extractor, tmp_path):
        """Test supports for .url files."""
        url_file = tmp_path / "bookmark.url"
        url_file.write_text("[InternetShortcut]\nURL=https://example.com")
        
        # .url files should be extractable
        assert extractor.supports(str(url_file))


class TestWebExtractorURLFile:
    """Tests for .url file handling."""

    @pytest.fixture
    def extractor(self):
        return WebExtractor()

    def test_read_url_file_standard(self, extractor, tmp_path):
        """Test reading standard .url file format."""
        url_file = tmp_path / "test.url"
        url_file.write_text("[InternetShortcut]\nURL=https://example.com/page")
        
        url = extractor._read_url_file(url_file)
        assert url == "https://example.com/page"

    def test_read_url_file_plain(self, extractor, tmp_path):
        """Test reading plain text .url file."""
        url_file = tmp_path / "test.url"
        url_file.write_text("https://example.com/page")
        
        url = extractor._read_url_file(url_file)
        assert url == "https://example.com/page"

    def test_read_url_file_with_whitespace(self, extractor, tmp_path):
        """Test reading .url file with whitespace."""
        url_file = tmp_path / "test.url"
        url_file.write_text("  https://example.com/page  \n")
        
        url = extractor._read_url_file(url_file)
        assert url == "https://example.com/page"


class TestWebExtractorRealExtraction:
    """Real extraction tests (requires network)."""

    @pytest.fixture
    def extractor(self):
        return WebExtractor()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_extract_simple_page(self, extractor):
        """Test extracting a simple web page."""
        # Use a reliable, simple page
        result = await extractor.extract("https://example.com")
        
        assert result is not None
        assert result.media_type == MediaType.WEB
        assert len(result.markdown) > 0
        assert "Example Domain" in result.markdown or "example" in result.markdown.lower()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_extract_page_title(self, extractor):
        """Test that page title is extracted."""
        result = await extractor.extract("https://example.com")
        
        assert result.title is not None
        assert len(result.title) > 0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_extract_page_metadata(self, extractor):
        """Test that metadata is captured."""
        result = await extractor.extract("https://example.com")
        
        assert result.metadata is not None
        assert result.source == "https://example.com"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_extract_invalid_url(self, extractor):
        """Test extracting from invalid URL."""
        result = await extractor.extract("https://this-domain-does-not-exist-12345.com")
        
        # Should return error result
        assert result is not None
        assert "Error" in result.markdown or "error" in result.metadata.get("error", "")

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_extract_python_docs(self, extractor):
        """Test extracting Python documentation page."""
        result = await extractor.extract("https://docs.python.org/3/tutorial/appetite.html")
        
        assert result is not None
        assert len(result.markdown) > 100
        # Should contain some Python-related content
        assert "Python" in result.markdown or "python" in result.markdown.lower()


class TestWebExtractorStrategies:
    """Tests for different crawl strategies."""

    def test_bfs_strategy(self):
        """Test BFS strategy configuration."""
        extractor = WebExtractor(strategy="bfs")
        assert extractor.strategy == "bfs"

    def test_dfs_strategy(self):
        """Test DFS strategy configuration."""
        extractor = WebExtractor(strategy="dfs")
        assert extractor.strategy == "dfs"

    def test_bestfirst_strategy(self):
        """Test BestFirst strategy configuration."""
        extractor = WebExtractor(strategy="bestfirst")
        assert extractor.strategy == "bestfirst"


class TestWebExtractorPatterns:
    """Tests for URL pattern filtering."""

    def test_include_patterns(self):
        """Test include patterns configuration."""
        extractor = WebExtractor(include_patterns=["*/docs/*", "*/api/*"])
        assert "*/docs/*" in extractor.include_patterns
        assert "*/api/*" in extractor.include_patterns

    def test_exclude_patterns(self):
        """Test exclude patterns configuration."""
        extractor = WebExtractor(exclude_patterns=["*/login/*", "*/admin/*"])
        assert "*/login/*" in extractor.exclude_patterns
        assert "*/admin/*" in extractor.exclude_patterns

    def test_same_domain_restriction(self):
        """Test same domain restriction."""
        extractor = WebExtractor(same_domain=True)
        assert extractor.same_domain is True
        
        extractor2 = WebExtractor(same_domain=False)
        assert extractor2.same_domain is False


class TestWebExtractorEdgeCases:
    """Edge case tests for Web extractor."""

    @pytest.fixture
    def extractor(self):
        return WebExtractor()

    def test_empty_url(self, extractor):
        """Test with empty URL."""
        assert not extractor.supports("")

    def test_whitespace_url(self, extractor):
        """Test with whitespace URL."""
        assert not extractor.supports("   ")

    def test_url_with_query_params(self, extractor):
        """Test URL with query parameters."""
        assert extractor.supports("https://example.com/page?param=value&other=123")

    def test_url_with_fragment(self, extractor):
        """Test URL with fragment."""
        assert extractor.supports("https://example.com/page#section")

    def test_url_with_port(self, extractor):
        """Test URL with port number."""
        assert extractor.supports("https://example.com:8080/page")

    def test_url_with_auth(self, extractor):
        """Test URL with authentication."""
        assert extractor.supports("https://user:pass@example.com/page")
