"""Unit tests for GitHub extractor."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import base64

from ingestor.extractors.github.github_extractor import GitHubExtractor
from ingestor.types import MediaType


class TestGitHubExtractor:
    """Tests for GitHubExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create a GitHubExtractor instance."""
        return GitHubExtractor()

    @pytest.fixture
    def extractor_with_token(self):
        """Create a GitHubExtractor with a token."""
        return GitHubExtractor(token="test_token")

    # =========================================================================
    # URL Parsing Tests
    # =========================================================================

    def test_parse_repo_url(self, extractor):
        """Test parsing repository root URL."""
        url = "https://github.com/owner/repo"
        parsed = extractor._parse_github_url(url)

        assert parsed is not None
        assert parsed["owner"] == "owner"
        assert parsed["repo"] == "repo"
        assert parsed["url_type"] == "repo"
        assert parsed["branch"] is None
        assert parsed["path"] == ""

    def test_parse_repo_url_with_trailing_slash(self, extractor):
        """Test parsing repository URL with trailing slash."""
        url = "https://github.com/owner/repo/"
        parsed = extractor._parse_github_url(url)

        assert parsed is not None
        assert parsed["owner"] == "owner"
        assert parsed["repo"] == "repo"
        assert parsed["url_type"] == "repo"

    def test_parse_file_url(self, extractor):
        """Test parsing file blob URL."""
        url = "https://github.com/owner/repo/blob/main/src/file.py"
        parsed = extractor._parse_github_url(url)

        assert parsed is not None
        assert parsed["owner"] == "owner"
        assert parsed["repo"] == "repo"
        assert parsed["branch"] == "main"
        assert parsed["path"] == "src/file.py"
        assert parsed["url_type"] == "file"

    def test_parse_tree_url(self, extractor):
        """Test parsing directory tree URL."""
        url = "https://github.com/owner/repo/tree/develop/src"
        parsed = extractor._parse_github_url(url)

        assert parsed is not None
        assert parsed["owner"] == "owner"
        assert parsed["repo"] == "repo"
        assert parsed["branch"] == "develop"
        assert parsed["path"] == "src"
        assert parsed["url_type"] == "tree"

    def test_parse_raw_url(self, extractor):
        """Test parsing raw file URL."""
        url = "https://github.com/owner/repo/raw/main/README.md"
        parsed = extractor._parse_github_url(url)

        assert parsed is not None
        assert parsed["owner"] == "owner"
        assert parsed["repo"] == "repo"
        assert parsed["branch"] == "main"
        assert parsed["path"] == "README.md"
        assert parsed["url_type"] == "raw"

    def test_parse_invalid_url(self, extractor):
        """Test parsing invalid URL returns None."""
        url = "https://gitlab.com/owner/repo"
        parsed = extractor._parse_github_url(url)
        assert parsed is None

    def test_parse_non_github_url(self, extractor):
        """Test parsing non-GitHub URL returns None."""
        url = "https://example.com/path"
        parsed = extractor._parse_github_url(url)
        assert parsed is None

    # =========================================================================
    # Supports Method Tests
    # =========================================================================

    def test_supports_github_repo(self, extractor):
        """Test supports returns True for GitHub repo URL."""
        assert extractor.supports("https://github.com/owner/repo") is True

    def test_supports_github_file(self, extractor):
        """Test supports returns True for GitHub file URL."""
        assert extractor.supports("https://github.com/owner/repo/blob/main/file.py") is True

    def test_supports_github_tree(self, extractor):
        """Test supports returns True for GitHub tree URL."""
        assert extractor.supports("https://github.com/owner/repo/tree/main/src") is True

    def test_supports_www_github(self, extractor):
        """Test supports returns True for www.github.com."""
        assert extractor.supports("https://www.github.com/owner/repo") is True

    def test_not_supports_gitlab(self, extractor):
        """Test supports returns False for GitLab URL."""
        assert extractor.supports("https://gitlab.com/owner/repo") is False

    def test_not_supports_local_file(self, extractor):
        """Test supports returns False for local file path."""
        assert extractor.supports("/path/to/file.py") is False

    def test_not_supports_other_url(self, extractor):
        """Test supports returns False for other URLs."""
        assert extractor.supports("https://example.com") is False

    # =========================================================================
    # Language Detection Tests
    # =========================================================================

    def test_get_language_python(self, extractor):
        """Test language detection for Python files."""
        assert extractor._get_language("src/main.py") == "python"

    def test_get_language_javascript(self, extractor):
        """Test language detection for JavaScript files."""
        assert extractor._get_language("app.js") == "javascript"

    def test_get_language_typescript(self, extractor):
        """Test language detection for TypeScript files."""
        assert extractor._get_language("src/index.ts") == "typescript"

    def test_get_language_json(self, extractor):
        """Test language detection for JSON files."""
        assert extractor._get_language("package.json") == "json"

    def test_get_language_yaml(self, extractor):
        """Test language detection for YAML files."""
        assert extractor._get_language("config.yaml") == "yaml"
        assert extractor._get_language("config.yml") == "yaml"

    def test_get_language_markdown(self, extractor):
        """Test language detection for Markdown files."""
        assert extractor._get_language("README.md") == "markdown"

    def test_get_language_dockerfile(self, extractor):
        """Test language detection for Dockerfile."""
        assert extractor._get_language("Dockerfile") == "dockerfile"

    def test_get_language_makefile(self, extractor):
        """Test language detection for Makefile."""
        assert extractor._get_language("Makefile") == "makefile"

    def test_get_language_unknown(self, extractor):
        """Test language detection for unknown extension."""
        assert extractor._get_language("file.xyz") == "text"

    # =========================================================================
    # Headers Tests
    # =========================================================================

    def test_headers_without_token(self, extractor):
        """Test headers without authentication token."""
        headers = extractor._get_headers()

        assert "Accept" in headers
        assert "User-Agent" in headers
        assert "Authorization" not in headers

    def test_headers_with_token(self, extractor_with_token):
        """Test headers with authentication token."""
        headers = extractor_with_token._get_headers()

        assert "Accept" in headers
        assert "User-Agent" in headers
        assert "Authorization" in headers
        assert headers["Authorization"] == "token test_token"

    # =========================================================================
    # Media Type Tests
    # =========================================================================

    def test_media_type(self, extractor):
        """Test that media_type is GITHUB."""
        assert extractor.media_type == MediaType.GITHUB

    # =========================================================================
    # Configuration Tests
    # =========================================================================

    def test_default_configuration(self, extractor):
        """Test default configuration values."""
        assert extractor.token is None
        assert extractor.include_code is True
        assert extractor.max_files == 50
        assert extractor.max_file_size == 100_000

    def test_custom_configuration(self):
        """Test custom configuration values."""
        extractor = GitHubExtractor(
            token="my_token",
            include_code=False,
            max_files=20,
            max_file_size=50_000,
        )

        assert extractor.token == "my_token"
        assert extractor.include_code is False
        assert extractor.max_files == 20
        assert extractor.max_file_size == 50_000


class TestGitHubExtractorAsync:
    """Async tests for GitHubExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create a GitHubExtractor instance."""
        return GitHubExtractor()

    @pytest.mark.asyncio
    async def test_extract_invalid_url(self, extractor):
        """Test extraction with invalid URL returns error."""
        result = await extractor.extract("https://gitlab.com/owner/repo")

        assert result.media_type == MediaType.GITHUB
        assert "Error" in result.markdown
        assert "Invalid GitHub URL" in result.markdown

    @pytest.mark.asyncio
    async def test_extract_repository_mock(self, extractor):
        """Test repository extraction with mocked API."""
        mock_repo_data = {
            "full_name": "owner/repo",
            "description": "Test repository",
            "default_branch": "main",
            "stargazers_count": 100,
            "forks_count": 10,
            "language": "Python",
            "license": {"name": "MIT"},
            "topics": ["python", "testing"],
        }

        mock_readme = "# Test Repo\n\nThis is a test."

        mock_tree = {
            "tree": [
                {"path": "README.md", "type": "blob", "size": 100},
                {"path": "src/main.py", "type": "blob", "size": 500},
            ]
        }

        with patch.object(extractor, "_api_request", new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = [mock_repo_data, mock_tree]

            with patch.object(extractor, "_get_readme", new_callable=AsyncMock) as mock_readme_fn:
                mock_readme_fn.return_value = mock_readme

                with patch.object(extractor, "_get_file_content", new_callable=AsyncMock) as mock_content:
                    mock_content.return_value = "print('hello')"

                    result = await extractor.extract("https://github.com/owner/repo")

        assert result.media_type == MediaType.GITHUB
        assert result.title == "owner/repo"
        assert "owner/repo" in result.markdown
        assert "Test repository" in result.markdown
        assert "100" in result.markdown  # stars
        assert "Python" in result.markdown

    @pytest.mark.asyncio
    async def test_extract_file_mock(self, extractor):
        """Test file extraction with mocked API."""
        mock_content = "def hello():\n    print('Hello, World!')"

        with patch.object(extractor, "_get_file_content", new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = mock_content

            result = await extractor.extract(
                "https://github.com/owner/repo/blob/main/src/hello.py"
            )

        assert result.media_type == MediaType.GITHUB
        assert result.title == "hello.py"
        assert "def hello()" in result.markdown
        assert "```python" in result.markdown

    @pytest.mark.asyncio
    async def test_extract_directory_mock(self, extractor):
        """Test directory extraction with mocked API."""
        mock_contents = [
            {"name": "subdir", "type": "dir", "path": "src/subdir"},
            {"name": "main.py", "type": "file", "path": "src/main.py", "size": 500},
            {"name": "utils.py", "type": "file", "path": "src/utils.py", "size": 300},
        ]

        with patch.object(extractor, "_api_request", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = mock_contents

            with patch.object(extractor, "_get_file_content", new_callable=AsyncMock) as mock_content:
                mock_content.return_value = "# code"

                result = await extractor.extract(
                    "https://github.com/owner/repo/tree/main/src"
                )

        assert result.media_type == MediaType.GITHUB
        assert "subdir" in result.markdown
        assert "main.py" in result.markdown
        assert "utils.py" in result.markdown

    @pytest.mark.asyncio
    async def test_get_readme_mock(self, extractor):
        """Test README fetching with mocked API."""
        readme_content = "# My Project\n\nDescription here."
        encoded_content = base64.b64encode(readme_content.encode()).decode()

        mock_response = {"content": encoded_content}

        with patch.object(extractor, "_api_request", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = mock_response

            result = await extractor._get_readme("owner", "repo")

        assert result == readme_content

    @pytest.mark.asyncio
    async def test_get_file_content_mock(self, extractor):
        """Test file content fetching with mocked API."""
        file_content = "print('hello')"
        encoded_content = base64.b64encode(file_content.encode()).decode()

        mock_response = {"content": encoded_content}

        with patch.object(extractor, "_api_request", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = mock_response

            result = await extractor._get_file_content("owner", "repo", "main", "file.py")

        assert result == file_content


class TestGitHubFileFiltering:
    """Tests for file filtering logic."""

    @pytest.fixture
    def extractor(self):
        """Create a GitHubExtractor instance."""
        return GitHubExtractor()

    def test_code_extensions(self, extractor):
        """Test that common code extensions are included."""
        assert ".py" in extractor.CODE_EXTENSIONS
        assert ".js" in extractor.CODE_EXTENSIONS
        assert ".ts" in extractor.CODE_EXTENSIONS
        assert ".go" in extractor.CODE_EXTENSIONS
        assert ".rs" in extractor.CODE_EXTENSIONS

    def test_important_files(self, extractor):
        """Test that important files are included."""
        assert "readme.md" in extractor.IMPORTANT_FILES
        assert "license" in extractor.IMPORTANT_FILES
        assert "requirements.txt" in extractor.IMPORTANT_FILES
        assert "package.json" in extractor.IMPORTANT_FILES
        assert "dockerfile" in extractor.IMPORTANT_FILES
