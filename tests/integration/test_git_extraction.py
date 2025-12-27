"""Integration tests for Git extraction."""

import pytest

from ingestor.core.detector import FileDetector
from ingestor.extractors.git.git_extractor import GitExtractor, GitRepoConfig
from ingestor.types import MediaType

# Mark all tests in this module as requiring network access
pytestmark = pytest.mark.network


class TestGitDetection:
    """Test Git URL detection in FileDetector."""

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

    def test_detect_ssh_url(self, detector):
        """Test detection of SSH git URL."""
        result = detector.detect("git@github.com:user/repo.git")
        assert result == MediaType.GIT

    def test_detect_www_github_url(self, detector):
        """Test detection of www.github.com URL."""
        result = detector.detect("https://www.github.com/python/cpython")
        assert result == MediaType.GITHUB

    def test_youtube_not_detected_as_git(self, detector):
        """Test that YouTube URLs are not detected as Git."""
        result = detector.detect("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert result == MediaType.YOUTUBE

    def test_generic_web_not_detected_as_git(self, detector):
        """Test that generic web URLs are not detected as Git."""
        result = detector.detect("https://example.com/path")
        assert result == MediaType.WEB


class TestGitExtraction:
    """Integration tests for Git extraction with real operations."""

    @pytest.fixture
    def extractor(self):
        """Create a GitExtractor instance with limited files."""
        config = GitRepoConfig(max_total_files=10)
        return GitExtractor(config=config)

    @pytest.mark.asyncio
    async def test_extract_small_repo_clone(self, extractor):
        """Test cloning a small public repository."""
        # Using octocat/Hello-World as it's tiny
        result = await extractor.extract("https://github.com/octocat/Hello-World")

        assert result.media_type == MediaType.GIT
        assert result.title is not None
        assert result.source == "https://github.com/octocat/Hello-World"
        assert len(result.markdown) > 0

    @pytest.mark.asyncio
    async def test_extract_github_single_file(self, extractor):
        """Test extracting a single file via GitHub API."""
        result = await extractor.extract(
            "https://github.com/octocat/Hello-World/blob/master/README"
        )

        assert result.media_type == MediaType.GIT
        assert "README" in result.title
        assert len(result.markdown) > 0

    @pytest.mark.asyncio
    async def test_supports_method(self, extractor):
        """Test supports method with various URLs."""
        # Should support
        assert extractor.supports("https://github.com/owner/repo") is True
        assert extractor.supports("https://github.com/owner/repo/blob/main/file.py") is True
        assert extractor.supports("https://www.github.com/owner/repo") is True
        assert extractor.supports("git@github.com:owner/repo.git") is True
        assert extractor.supports("repos.download_git") is True

        # Should not support
        assert extractor.supports("https://example.com") is False


class TestGitCloneOptions:
    """Tests for git clone options."""

    @pytest.mark.asyncio
    async def test_shallow_clone(self):
        """Test shallow clone with depth=1."""
        config = GitRepoConfig(shallow=True, depth=1, max_total_files=5)
        extractor = GitExtractor(config=config)

        result = await extractor.extract("https://github.com/octocat/Hello-World")

        assert result.media_type == MediaType.GIT
        assert "Hello-World" in result.title or "octocat" in result.title

    @pytest.mark.asyncio
    async def test_clone_with_file_limit(self):
        """Test clone with file limit."""
        config = GitRepoConfig(max_total_files=3)
        extractor = GitExtractor(config=config)

        result = await extractor.extract("https://github.com/octocat/Hello-World")

        assert result.media_type == MediaType.GIT
        # Should still produce output even with limit
        assert len(result.markdown) > 0


class TestGitHubAPIExtraction:
    """Tests for GitHub API-based extraction."""

    @pytest.fixture
    def extractor(self):
        """Create a GitExtractor instance."""
        return GitExtractor()

    @pytest.mark.asyncio
    async def test_extract_nonexistent_repo(self, extractor):
        """Test extracting a nonexistent repository returns error."""
        result = await extractor.extract(
            "https://github.com/nonexistent-user-12345/nonexistent-repo-67890"
        )

        # Should contain error info (either in markdown or metadata)
        markdown_lower = result.markdown.lower()
        assert "error" in markdown_lower or "failed" in markdown_lower or result.metadata.get("error")

    @pytest.mark.asyncio
    async def test_extract_directory_via_api(self, extractor):
        """Test extracting a directory."""
        result = await extractor.extract(
            "https://github.com/octocat/Hello-World/tree/master"
        )

        assert result.media_type == MediaType.GIT
        # Should have some content
        assert len(result.markdown) > 0
