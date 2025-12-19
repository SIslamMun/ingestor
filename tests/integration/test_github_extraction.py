"""Integration tests for GitHub extraction."""

import pytest

from ingestor.extractors.github.github_extractor import GitHubExtractor
from ingestor.types import MediaType
from ingestor.core.detector import FileDetector


# Mark all tests in this module as requiring network access
pytestmark = pytest.mark.network


class TestGitHubDetection:
    """Test GitHub URL detection in FileDetector."""

    @pytest.fixture
    def detector(self):
        """Create a FileDetector instance."""
        return FileDetector()

    def test_detect_github_repo_url(self, detector):
        """Test detection of GitHub repository URL."""
        result = detector.detect("https://github.com/python/cpython")
        assert result == MediaType.GITHUB

    def test_detect_github_file_url(self, detector):
        """Test detection of GitHub file URL."""
        result = detector.detect("https://github.com/python/cpython/blob/main/README.rst")
        assert result == MediaType.GITHUB

    def test_detect_github_tree_url(self, detector):
        """Test detection of GitHub tree URL."""
        result = detector.detect("https://github.com/python/cpython/tree/main/Lib")
        assert result == MediaType.GITHUB

    def test_detect_www_github_url(self, detector):
        """Test detection of www.github.com URL."""
        result = detector.detect("https://www.github.com/python/cpython")
        assert result == MediaType.GITHUB

    def test_youtube_not_detected_as_github(self, detector):
        """Test that YouTube URLs are not detected as GitHub."""
        result = detector.detect("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert result == MediaType.YOUTUBE

    def test_generic_web_not_detected_as_github(self, detector):
        """Test that generic web URLs are not detected as GitHub."""
        result = detector.detect("https://example.com/path")
        assert result == MediaType.WEB


class TestGitHubExtraction:
    """Integration tests for GitHub extraction with real API calls."""

    @pytest.fixture
    def extractor(self):
        """Create a GitHubExtractor instance."""
        return GitHubExtractor()

    @pytest.mark.asyncio
    async def test_extract_small_repo(self, extractor):
        """Test extracting a small public repository."""
        # Using a small, stable repo for testing
        result = await extractor.extract("https://github.com/octocat/Hello-World")

        assert result.media_type == MediaType.GITHUB
        assert result.title is not None
        assert "Hello-World" in result.title or "octocat" in result.title
        assert result.source == "https://github.com/octocat/Hello-World"
        assert len(result.markdown) > 0

        # Check metadata
        assert result.metadata.get("owner") == "octocat"
        assert result.metadata.get("repo") == "Hello-World"

    @pytest.mark.asyncio
    async def test_extract_repo_with_readme(self, extractor):
        """Test extracting a repository with README."""
        result = await extractor.extract("https://github.com/octocat/Hello-World")

        # The markdown should contain repository info
        assert "Repository Info" in result.markdown or "octocat" in result.markdown

    @pytest.mark.asyncio
    async def test_extract_file(self, extractor):
        """Test extracting a single file."""
        # Extract a known file from Hello-World repo
        result = await extractor.extract(
            "https://github.com/octocat/Hello-World/blob/master/README"
        )

        assert result.media_type == MediaType.GITHUB
        assert "README" in result.title
        assert "Content" in result.markdown

    @pytest.mark.asyncio
    async def test_extract_nonexistent_repo(self, extractor):
        """Test extracting a nonexistent repository returns error."""
        result = await extractor.extract(
            "https://github.com/nonexistent-user-12345/nonexistent-repo-67890"
        )

        # Should contain error info (either in markdown or metadata)
        assert "Error" in result.markdown or result.metadata.get("error")

    @pytest.mark.asyncio
    async def test_extract_python_repo(self, extractor):
        """Test extracting a Python repository."""
        # Using requests library as it's a well-known, stable repo
        extractor_limited = GitHubExtractor(max_files=5)
        result = await extractor_limited.extract("https://github.com/psf/requests")

        assert result.media_type == MediaType.GITHUB
        assert "requests" in result.title.lower()
        assert result.metadata.get("language") == "Python"

    @pytest.mark.asyncio
    async def test_metadata_extraction(self, extractor):
        """Test that metadata is properly extracted."""
        result = await extractor.extract("https://github.com/octocat/Hello-World")

        # Check required metadata fields
        assert "owner" in result.metadata
        assert "repo" in result.metadata
        assert "default_branch" in result.metadata

    @pytest.mark.asyncio
    async def test_supports_method(self, extractor):
        """Test supports method with various URLs."""
        # Should support
        assert extractor.supports("https://github.com/owner/repo") is True
        assert extractor.supports("https://github.com/owner/repo/blob/main/file.py") is True
        assert extractor.supports("https://www.github.com/owner/repo") is True

        # Should not support
        assert extractor.supports("https://gitlab.com/owner/repo") is False
        assert extractor.supports("https://bitbucket.org/owner/repo") is False
        assert extractor.supports("https://example.com") is False


class TestGitHubRateLimiting:
    """Tests related to API rate limiting."""

    @pytest.fixture
    def extractor(self):
        """Create a GitHubExtractor instance."""
        return GitHubExtractor()

    @pytest.mark.asyncio
    async def test_handles_rate_limit_gracefully(self, extractor):
        """Test that rate limiting is handled gracefully."""
        # This test just ensures the extractor doesn't crash
        # when making API requests
        result = await extractor.extract("https://github.com/octocat/Hello-World")

        # Should return a result even if rate limited
        assert result is not None
        assert result.media_type == MediaType.GITHUB


class TestGitHubDirectoryExtraction:
    """Tests for directory extraction."""

    @pytest.fixture
    def extractor(self):
        """Create a GitHubExtractor instance."""
        return GitHubExtractor(max_files=10)

    @pytest.mark.asyncio
    async def test_extract_directory(self, extractor):
        """Test extracting a directory."""
        result = await extractor.extract(
            "https://github.com/octocat/Hello-World/tree/master"
        )

        assert result.media_type == MediaType.GITHUB
        assert "Contents" in result.markdown or "Files" in result.markdown
