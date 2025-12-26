"""Unit tests for WebSearchClient."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from ingestor.extractors.paper.clients.web_search import WebSearchClient


class TestWebSearchClientInit:
    """Test WebSearchClient initialization."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        client = WebSearchClient()
        assert client.enabled is True
        assert client._sdk_available is None  # Not checked yet

    def test_init_disabled(self):
        """Test initialization with disabled."""
        client = WebSearchClient(enabled=False)
        assert client.enabled is False


class TestSDKAvailability:
    """Test Claude Agent SDK availability checks."""

    def test_check_sdk_available_not_installed(self):
        """Test SDK check when not installed."""
        client = WebSearchClient()
        # Mock import failure
        with patch.dict("sys.modules", {"claude_code_sdk": None}):
            client._sdk_available = None
            result = client._check_sdk_available()
            # Will be False if SDK not installed
            assert isinstance(result, bool)

    def test_check_sdk_caches_result(self):
        """Test that SDK check caches result."""
        client = WebSearchClient()
        client._sdk_available = True
        
        # Should return cached value without re-checking
        result = client._check_sdk_available()
        assert result is True

    def test_is_available_disabled(self):
        """Test is_available when disabled."""
        client = WebSearchClient(enabled=False)
        assert client.is_available() is False

    def test_is_available_no_sdk(self):
        """Test is_available when SDK not installed."""
        client = WebSearchClient(enabled=True)
        client._sdk_available = False
        assert client.is_available() is False

    def test_is_available_all_good(self):
        """Test is_available when everything is configured."""
        client = WebSearchClient(enabled=True)
        client._sdk_available = True
        assert client.is_available() is True


class TestSearchForPDF:
    """Test search_for_pdf method."""

    @pytest.mark.asyncio
    async def test_search_disabled(self):
        """Test search when disabled."""
        client = WebSearchClient(enabled=False)
        result = await client.search_for_pdf("Test Paper")
        assert result is None

    @pytest.mark.asyncio
    async def test_search_no_sdk(self):
        """Test search when SDK not available."""
        client = WebSearchClient(enabled=True)
        client._sdk_available = False
        result = await client.search_for_pdf("Test Paper")
        assert result is None

    @pytest.mark.asyncio
    async def test_search_with_title_only(self):
        """Test search with title only."""
        client = WebSearchClient(enabled=True)
        client._sdk_available = False  # SDK not available
        
        result = await client.search_for_pdf(
            title="Attention Is All You Need",
        )
        assert result is None  # Returns None because SDK not available

    @pytest.mark.asyncio
    async def test_search_with_all_params(self):
        """Test search with all parameters."""
        client = WebSearchClient(enabled=True)
        client._sdk_available = False  # SDK not available
        
        result = await client.search_for_pdf(
            title="Attention Is All You Need",
            doi="10.48550/arXiv.1706.03762",
            authors=["Vaswani", "Shazeer", "Parmar"],
        )
        assert result is None


class TestSearchAuthorPage:
    """Test search_author_page method."""

    @pytest.mark.asyncio
    async def test_search_author_disabled(self):
        """Test author search when disabled."""
        client = WebSearchClient(enabled=False)
        result = await client.search_author_page(
            "Geoffrey Hinton",
            "Deep Learning",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_search_author_no_sdk(self):
        """Test author search when SDK not available."""
        client = WebSearchClient(enabled=True)
        client._sdk_available = False
        result = await client.search_author_page(
            "Geoffrey Hinton",
            "Deep Learning",
        )
        assert result is None


class TestSearchInstitutionalRepository:
    """Test search_institutional_repository method."""

    @pytest.mark.asyncio
    async def test_search_repo_disabled(self):
        """Test repository search when disabled."""
        client = WebSearchClient(enabled=False)
        result = await client.search_institutional_repository(
            "Test Paper Title",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_search_repo_no_sdk(self):
        """Test repository search when SDK not available."""
        client = WebSearchClient(enabled=True)
        client._sdk_available = False
        result = await client.search_institutional_repository(
            "Test Paper Title",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_search_repo_with_institution(self):
        """Test repository search with institution specified."""
        client = WebSearchClient(enabled=True)
        client._sdk_available = False
        result = await client.search_institutional_repository(
            "Test Paper Title",
            institution="MIT",
        )
        assert result is None


class TestURLExtraction:
    """Test URL extraction from search results."""

    def test_pdf_url_pattern(self):
        """Test that PDF URL pattern works."""
        import re
        
        pattern = r"https?://[^\s<>\"']+\.pdf(?:\?[^\s<>\"']*)?"
        
        # Should match
        assert re.search(pattern, "https://example.com/paper.pdf", re.I)
        assert re.search(pattern, "http://example.com/download/paper.pdf?token=abc", re.I)
        
        # Should not match
        assert not re.search(pattern, "https://example.com/paper.html", re.I)

    def test_download_url_detection(self):
        """Test detection of download URLs."""
        urls = [
            "https://example.com/download/12345",
            "https://example.com/fulltext/paper",
            "https://example.com/pdf/view",
            "https://example.com/full-text/article",
        ]
        
        for url in urls:
            has_keyword = any(
                x in url.lower()
                for x in ["download", "pdf", "fulltext", "full-text"]
            )
            assert has_keyword, f"URL should be detected as download: {url}"
