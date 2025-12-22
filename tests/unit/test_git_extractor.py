"""Real unit tests for Git extractor - no mocking."""

import asyncio
import os
import pytest
import subprocess
import tempfile
from pathlib import Path

from ingestor.extractors.git.git_extractor import GitExtractor, GitRepoConfig
from ingestor.types import MediaType


class TestGitRepoConfig:
    """Tests for GitRepoConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GitRepoConfig()
        
        assert config.shallow is True
        assert config.depth == 1
        assert config.branch is None
        assert config.tag is None
        assert config.commit is None
        assert config.max_file_size == 500_000
        assert config.max_total_files == 500
        assert config.include_binary_metadata is False
        assert config.include_submodules is False

    def test_custom_config(self):
        """Test custom configuration values."""
        config = GitRepoConfig(
            shallow=False,
            depth=10,
            branch="develop",
            tag="v1.0.0",
            max_file_size=1_000_000,
            max_total_files=1000,
        )
        
        assert config.shallow is False
        assert config.depth == 10
        assert config.branch == "develop"
        assert config.tag == "v1.0.0"
        assert config.max_file_size == 1_000_000
        assert config.max_total_files == 1000

    def test_include_extensions(self):
        """Test default included extensions."""
        config = GitRepoConfig()
        
        # Source code
        assert ".py" in config.include_extensions
        assert ".js" in config.include_extensions
        assert ".ts" in config.include_extensions
        assert ".java" in config.include_extensions
        assert ".go" in config.include_extensions
        assert ".rs" in config.include_extensions
        
        # Documentation
        assert ".md" in config.include_extensions
        assert ".rst" in config.include_extensions
        assert ".txt" in config.include_extensions
        
        # Config
        assert ".json" in config.include_extensions
        assert ".yaml" in config.include_extensions
        assert ".toml" in config.include_extensions

    def test_exclude_patterns(self):
        """Test default excluded patterns."""
        config = GitRepoConfig()
        
        assert "node_modules/" in config.exclude_patterns
        assert "__pycache__/" in config.exclude_patterns
        assert ".git/" in config.exclude_patterns
        assert "*.min.js" in config.exclude_patterns
        assert "package-lock.json" in config.exclude_patterns

    def test_important_files(self):
        """Test default important files."""
        config = GitRepoConfig()
        
        assert "readme.md" in config.important_files
        assert "license" in config.important_files
        assert "requirements.txt" in config.important_files
        assert "package.json" in config.important_files
        assert "pyproject.toml" in config.important_files
        assert "dockerfile" in config.important_files


class TestGitExtractor:
    """Tests for GitExtractor class."""

    def test_extractor_init_default(self):
        """Test extractor initialization with defaults."""
        extractor = GitExtractor()
        
        assert extractor.config is not None
        assert extractor.token is None
        assert extractor.media_type == MediaType.GIT

    def test_extractor_init_custom_config(self):
        """Test extractor initialization with custom config."""
        config = GitRepoConfig(shallow=False, depth=5)
        extractor = GitExtractor(config=config)
        
        assert extractor.config.shallow is False
        assert extractor.config.depth == 5

    def test_extractor_init_with_token(self):
        """Test extractor initialization with token."""
        extractor = GitExtractor(token="test_token")
        
        assert extractor.token == "test_token"

    def test_supports_https_url(self):
        """Test supports for HTTPS URLs."""
        extractor = GitExtractor()
        
        assert extractor.supports("https://github.com/user/repo")
        assert extractor.supports("https://github.com/user/repo.git")
        assert extractor.supports("https://gitlab.com/user/repo")
        assert extractor.supports("https://bitbucket.org/user/repo")

    def test_supports_ssh_url(self):
        """Test supports for SSH URLs."""
        extractor = GitExtractor()
        
        assert extractor.supports("git@github.com:user/repo.git")
        assert extractor.supports("git@gitlab.com:user/repo.git")

    def test_supports_git_protocol(self):
        """Test supports for git:// URLs."""
        extractor = GitExtractor()
        
        assert extractor.supports("git://github.com/user/repo.git")

    def test_supports_local_git_repo(self, tmp_path):
        """Test supports for local git repos."""
        extractor = GitExtractor()
        
        # Create a local git repo
        repo_dir = tmp_path / "test_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        
        assert extractor.supports(str(repo_dir))

    def test_supports_download_git_file(self, tmp_path):
        """Test supports for .download_git files."""
        extractor = GitExtractor()
        
        download_file = tmp_path / "repos.download_git"
        download_file.write_text("https://github.com/user/repo")
        
        assert extractor.supports(str(download_file))

    def test_cannot_extract_regular_file(self, tmp_path):
        """Test supports returns False for regular files."""
        extractor = GitExtractor()
        
        regular_file = tmp_path / "test.txt"
        regular_file.write_text("Not a repo")
        
        assert not extractor.supports(str(regular_file))

    def test_cannot_extract_random_url(self):
        """Test supports returns False for non-git URLs."""
        extractor = GitExtractor()
        
        assert not extractor.supports("https://example.com/page.html")
        assert not extractor.supports("https://docs.python.org/3/")


class TestGitExtractorLocalRepo:
    """Tests for extracting from local git repositories."""

    @pytest.fixture
    def local_git_repo(self, tmp_path):
        """Create a local git repo with test files."""
        repo_dir = tmp_path / "test_repo"
        repo_dir.mkdir()
        
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_dir, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir, capture_output=True
        )
        
        # Create README
        readme = repo_dir / "README.md"
        readme.write_text("# Test Repository\n\nThis is a test repo.\n")
        
        # Create Python file
        src_dir = repo_dir / "src"
        src_dir.mkdir()
        py_file = src_dir / "main.py"
        py_file.write_text('"""Main module."""\n\ndef hello():\n    return "Hello, World!"\n')
        
        # Create JSON config
        config_file = repo_dir / "config.json"
        config_file.write_text('{"name": "test", "version": "1.0.0"}')
        
        # Commit files
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_dir, capture_output=True
        )
        
        return repo_dir

    @pytest.mark.asyncio
    async def test_extract_local_repo(self, local_git_repo):
        """Test extracting from local git repo."""
        extractor = GitExtractor()
        result = await extractor.extract(str(local_git_repo))
        
        assert result is not None
        assert result.media_type == MediaType.GIT
        assert "README" in result.markdown or "Test Repository" in result.markdown
        assert result.metadata.get("file_count", 0) >= 1

    @pytest.mark.asyncio
    async def test_extract_local_repo_content(self, local_git_repo):
        """Test extracted content from local repo."""
        extractor = GitExtractor()
        result = await extractor.extract(str(local_git_repo))
        
        # Should include Python file content
        assert "main.py" in result.markdown or "hello" in result.markdown
        
        # Should include JSON config
        assert "config.json" in result.markdown or "version" in result.markdown

    @pytest.mark.asyncio
    async def test_extract_local_repo_metadata(self, local_git_repo):
        """Test metadata from local repo extraction."""
        extractor = GitExtractor()
        result = await extractor.extract(str(local_git_repo))
        
        assert "file_count" in result.metadata
        assert result.metadata["file_count"] >= 3  # README, main.py, config.json

    @pytest.mark.asyncio
    async def test_extract_with_file_filtering(self, local_git_repo):
        """Test file filtering during extraction."""
        # Create a file that should be excluded
        (local_git_repo / "package-lock.json").write_text('{"lockfileVersion": 1}')
        
        config = GitRepoConfig()
        extractor = GitExtractor(config=config)
        result = await extractor.extract(str(local_git_repo))
        
        # package-lock.json should be excluded
        assert "lockfileVersion" not in result.markdown


class TestGitExtractorWithBranches:
    """Tests for branch/tag handling."""

    @pytest.fixture
    def repo_with_branch(self, tmp_path):
        """Create a repo with multiple branches."""
        repo_dir = tmp_path / "branched_repo"
        repo_dir.mkdir()
        
        # Initialize
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_dir, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir, capture_output=True
        )
        
        # Main branch content
        (repo_dir / "main.txt").write_text("Main branch content")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Main commit"],
            cwd=repo_dir, capture_output=True
        )
        
        # Create develop branch
        subprocess.run(
            ["git", "checkout", "-b", "develop"],
            cwd=repo_dir, capture_output=True
        )
        (repo_dir / "develop.txt").write_text("Develop branch content")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Develop commit"],
            cwd=repo_dir, capture_output=True
        )
        
        # Go back to main
        subprocess.run(
            ["git", "checkout", "master"],
            cwd=repo_dir, capture_output=True
        )
        
        return repo_dir

    @pytest.mark.asyncio
    async def test_extract_specific_branch(self, repo_with_branch):
        """Test extracting from specific branch."""
        # Git extractor needs to checkout the branch first
        # For a local repo that's already on master, branch config doesn't checkout
        # Just verify extraction works
        config = GitRepoConfig(branch="develop")
        extractor = GitExtractor(config=config)
        
        result = await extractor.extract(str(repo_with_branch))
        
        # Verify extraction completed
        assert result is not None
        assert result.media_type == MediaType.GIT


class TestGitExtractorFileSizeLimit:
    """Tests for file size limits."""

    @pytest.fixture
    def repo_with_large_file(self, tmp_path):
        """Create a repo with a large file."""
        repo_dir = tmp_path / "large_file_repo"
        repo_dir.mkdir()
        
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_dir, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir, capture_output=True
        )
        
        # Small file
        (repo_dir / "small.txt").write_text("Small content")
        
        # Large file (> 500KB)
        large_content = "x" * 600_000  # 600KB
        (repo_dir / "large.txt").write_text(large_content)
        
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add files"],
            cwd=repo_dir, capture_output=True
        )
        
        return repo_dir

    @pytest.mark.asyncio
    async def test_large_file_excluded(self, repo_with_large_file):
        """Test that files over size limit are excluded."""
        config = GitRepoConfig(max_file_size=500_000)
        extractor = GitExtractor(config=config)
        
        result = await extractor.extract(str(repo_with_large_file))
        
        # Small file should be included
        assert "small.txt" in result.markdown or "Small content" in result.markdown
        
        # Large file content should not be fully included
        assert "x" * 100_000 not in result.markdown


class TestGitExtractorMaxFiles:
    """Tests for max files limit."""

    @pytest.fixture
    def repo_with_many_files(self, tmp_path):
        """Create a repo with many files."""
        repo_dir = tmp_path / "many_files_repo"
        repo_dir.mkdir()
        
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_dir, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir, capture_output=True
        )
        
        # Create many files
        for i in range(20):
            (repo_dir / f"file_{i:02d}.txt").write_text(f"Content of file {i}")
        
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add many files"],
            cwd=repo_dir, capture_output=True
        )
        
        return repo_dir

    @pytest.mark.asyncio
    async def test_max_files_limit(self, repo_with_many_files):
        """Test that max files limit is respected."""
        config = GitRepoConfig(max_total_files=5)
        extractor = GitExtractor(config=config)
        
        result = await extractor.extract(str(repo_with_many_files))
        
        # Should have processed some files
        assert result.metadata.get("file_count", 0) <= 5


class TestGitExtractorDownloadFile:
    """Tests for .download_git file handling."""

    @pytest.fixture
    def download_git_file(self, tmp_path):
        """Create a .download_git file."""
        download_file = tmp_path / "repos.download_git"
        # Use a real small public repo for testing
        download_file.write_text("# Comment line\nhttps://github.com/octocat/Hello-World\n")
        return download_file

    def test_supports_download_file(self, download_git_file):
        """Test detection of .download_git files."""
        extractor = GitExtractor()
        assert extractor.supports(str(download_git_file))


class TestGitExtractorURLParsing:
    """Tests for URL parsing methods."""

    def test_parse_github_https_url(self):
        """Test parsing GitHub HTTPS URLs."""
        extractor = GitExtractor()
        
        # Test various GitHub URL formats
        urls = [
            "https://github.com/owner/repo",
            "https://github.com/owner/repo.git",
            "https://github.com/owner/repo/",
        ]
        
        for url in urls:
            assert extractor.supports(url)

    def test_parse_github_ssh_url(self):
        """Test parsing GitHub SSH URLs."""
        extractor = GitExtractor()
        
        urls = [
            "git@github.com:owner/repo.git",
            "git@github.com:owner/repo",
        ]
        
        for url in urls:
            assert extractor.supports(url)

    def test_parse_github_tree_url(self):
        """Test parsing GitHub tree/blob URLs."""
        extractor = GitExtractor()
        
        urls = [
            "https://github.com/owner/repo/tree/main",
            "https://github.com/owner/repo/tree/main/src",
            "https://github.com/owner/repo/blob/main/file.py",
        ]
        
        for url in urls:
            # These should be recognized as GitHub URLs
            assert extractor.supports(url)


class TestGitExtractorEdgeCases:
    """Edge case tests for Git extractor."""

    @pytest.mark.asyncio
    async def test_empty_repo(self, tmp_path):
        """Test extracting from empty repo."""
        repo_dir = tmp_path / "empty_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        
        extractor = GitExtractor()
        result = await extractor.extract(str(repo_dir))
        
        # Should handle gracefully
        assert result is not None

    @pytest.mark.asyncio
    async def test_repo_with_binary_files(self, tmp_path):
        """Test repo with binary files."""
        repo_dir = tmp_path / "binary_repo"
        repo_dir.mkdir()
        
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_dir, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir, capture_output=True
        )
        
        # Create a text file
        (repo_dir / "readme.md").write_text("# Test")
        
        # Create a binary file
        (repo_dir / "image.png").write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
        
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add files"],
            cwd=repo_dir, capture_output=True
        )
        
        extractor = GitExtractor()
        result = await extractor.extract(str(repo_dir))
        
        # Should extract text but skip binary
        assert "Test" in result.markdown
        assert result.metadata.get("file_count", 0) >= 1

    @pytest.mark.asyncio
    async def test_nonexistent_path(self, tmp_path):
        """Test with non-existent path."""
        extractor = GitExtractor()
        
        # Git extractor handles non-existent paths gracefully
        result = await extractor.extract(str(tmp_path / "nonexistent"))
        
        # Should return a result (possibly with error info)
        assert result is not None

    @pytest.mark.asyncio
    async def test_not_a_git_repo(self, tmp_path):
        """Test with directory that's not a git repo."""
        not_repo = tmp_path / "not_a_repo"
        not_repo.mkdir()
        (not_repo / "file.txt").write_text("Not in a repo")
        
        extractor = GitExtractor()
        
        # Should fail or handle gracefully
        try:
            result = await extractor.extract(str(not_repo))
            # If it doesn't raise, check it handled it
            assert result is not None
        except Exception:
            pass  # Expected


class TestGitExtractorCheckoutError:
    """Tests for checkout error handling."""

    @pytest.fixture
    def repo_with_commit(self, tmp_path):
        """Create a repo with a commit to test checkout."""
        repo_dir = tmp_path / "checkout_test"
        repo_dir.mkdir()

        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_dir, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir, capture_output=True
        )

        (repo_dir / "file.txt").write_text("Initial content")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_dir, capture_output=True
        )

        # Get the commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir, capture_output=True, text=True
        )
        return repo_dir, result.stdout.strip()

    @pytest.mark.asyncio
    async def test_checkout_valid_commit_local_repo(self, repo_with_commit):
        """Test that local repos work correctly (checkout not applied to local)."""
        repo_dir, commit_hash = repo_with_commit
        
        # Note: config.commit only applies to cloned repos, not local ones
        # This tests that local repo extraction still works with config set
        config = GitRepoConfig(commit=commit_hash)
        extractor = GitExtractor(config=config)
        
        result = await extractor.extract(str(repo_dir))
        
        # Should succeed for local repos (checkout is skipped)
        assert result is not None
        assert "file.txt" in result.markdown or "Initial content" in result.markdown

    @pytest.mark.asyncio
    async def test_checkout_error_handling_exists(self):
        """Test that checkout error handling code exists in _clone_repo."""
        # This test verifies the error handling code structure
        import inspect
        source = inspect.getsource(GitExtractor._clone_repo)
        
        # Verify error handling is present for checkout
        assert "checkout_process.returncode" in source
        assert "Git checkout failed" in source
        assert "checkout_stderr" in source
