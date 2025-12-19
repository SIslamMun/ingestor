"""GitHub repository extractor using GitHub API."""

import base64
import re
from pathlib import Path
from typing import List, Optional, Union
from urllib.parse import urlparse

from ...types import ExtractionResult, ExtractedImage, MediaType
from ..base import BaseExtractor


class GitHubExtractor(BaseExtractor):
    """Extract content from GitHub repositories.

    Supports:
    - Repository README extraction
    - Source code files extraction
    - Repository metadata (description, stars, forks, etc.)
    - Directory listing with file contents
    - Specific file extraction from URLs

    Uses the GitHub REST API (with optional authentication for higher rate limits).
    """

    media_type = MediaType.GITHUB

    # GitHub URL patterns
    GITHUB_PATTERNS = [
        r"^https?://github\.com/([^/]+)/([^/]+)/?$",  # repo root
        r"^https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)$",  # file
        r"^https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/?(.*)$",  # directory
        r"^https?://github\.com/([^/]+)/([^/]+)/raw/([^/]+)/(.+)$",  # raw file
    ]

    # File extensions to include in code extraction
    CODE_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h", ".hpp",
        ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala", ".r", ".R",
        ".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd",
        ".html", ".css", ".scss", ".sass", ".less",
        ".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".cfg", ".conf",
        ".md", ".rst", ".txt", ".markdown",
        ".sql", ".graphql", ".proto",
        ".dockerfile", ".dockerignore", ".gitignore", ".env.example",
        ".makefile", ".cmake",
    }

    # Files to always include (case-insensitive)
    IMPORTANT_FILES = {
        "readme.md", "readme.rst", "readme.txt", "readme",
        "license", "license.md", "license.txt",
        "contributing.md", "contributing",
        "changelog.md", "changelog", "changes.md",
        "requirements.txt", "setup.py", "pyproject.toml", "setup.cfg",
        "package.json", "tsconfig.json", "webpack.config.js",
        "cargo.toml", "go.mod", "go.sum",
        "makefile", "dockerfile", "docker-compose.yml", "docker-compose.yaml",
        ".gitignore", ".env.example",
    }

    def __init__(
        self,
        token: Optional[str] = None,
        include_code: bool = True,
        max_files: int = 50,
        max_file_size: int = 100_000,  # 100KB per file
    ):
        """Initialize GitHub extractor.

        Args:
            token: GitHub personal access token (optional, for higher rate limits)
            include_code: Whether to include source code files
            max_files: Maximum number of files to extract
            max_file_size: Maximum file size in bytes to extract
        """
        self.token = token
        self.include_code = include_code
        self.max_files = max_files
        self.max_file_size = max_file_size
        self._client = None

    def _get_headers(self) -> dict:
        """Get HTTP headers for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Ingestor/0.1.0",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    async def _api_request(self, url: str) -> dict:
        """Make an authenticated request to GitHub API.

        Args:
            url: API URL to request

        Returns:
            JSON response as dict
        """
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._get_headers(), timeout=30.0)
            response.raise_for_status()
            return response.json()

    async def _get_raw_content(self, url: str) -> str:
        """Get raw file content from GitHub.

        Args:
            url: Raw content URL

        Returns:
            File content as string
        """
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._get_headers(), timeout=30.0)
            response.raise_for_status()
            return response.text

    def _parse_github_url(self, url: str) -> dict:
        """Parse a GitHub URL to extract owner, repo, branch, and path.

        Args:
            url: GitHub URL

        Returns:
            Dict with owner, repo, branch, path, and url_type
        """
        url = str(url).rstrip("/")

        # Repository root: github.com/owner/repo
        match = re.match(r"^https?://github\.com/([^/]+)/([^/]+)/?$", url)
        if match:
            return {
                "owner": match.group(1),
                "repo": match.group(2),
                "branch": None,
                "path": "",
                "url_type": "repo",
            }

        # File: github.com/owner/repo/blob/branch/path
        match = re.match(r"^https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)$", url)
        if match:
            return {
                "owner": match.group(1),
                "repo": match.group(2),
                "branch": match.group(3),
                "path": match.group(4),
                "url_type": "file",
            }

        # Directory: github.com/owner/repo/tree/branch/path
        match = re.match(r"^https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/?(.*)$", url)
        if match:
            return {
                "owner": match.group(1),
                "repo": match.group(2),
                "branch": match.group(3),
                "path": match.group(4),
                "url_type": "tree",
            }

        # Raw file: github.com/owner/repo/raw/branch/path
        match = re.match(r"^https?://github\.com/([^/]+)/([^/]+)/raw/([^/]+)/(.+)$", url)
        if match:
            return {
                "owner": match.group(1),
                "repo": match.group(2),
                "branch": match.group(3),
                "path": match.group(4),
                "url_type": "raw",
            }

        return None

    async def extract(self, source: Union[str, Path]) -> ExtractionResult:
        """Extract content from a GitHub URL.

        Args:
            source: GitHub URL (repo, file, or directory)

        Returns:
            Extraction result with markdown content
        """
        url = str(source)
        parsed = self._parse_github_url(url)

        if not parsed:
            return ExtractionResult(
                markdown=f"# Error\n\nInvalid GitHub URL: {url}",
                title="Error",
                source=url,
                media_type=MediaType.GITHUB,
                images=[],
                metadata={"error": "Invalid GitHub URL"},
            )

        owner = parsed["owner"]
        repo = parsed["repo"]

        try:
            if parsed["url_type"] == "repo":
                return await self._extract_repository(owner, repo, url)
            elif parsed["url_type"] == "file":
                return await self._extract_file(owner, repo, parsed["branch"], parsed["path"], url)
            elif parsed["url_type"] == "tree":
                return await self._extract_directory(owner, repo, parsed["branch"], parsed["path"], url)
            elif parsed["url_type"] == "raw":
                return await self._extract_file(owner, repo, parsed["branch"], parsed["path"], url)
            else:
                return await self._extract_repository(owner, repo, url)
        except Exception as e:
            return ExtractionResult(
                markdown=f"# Error\n\nFailed to extract from GitHub: {url}\n\n{str(e)}",
                title="Error",
                source=url,
                media_type=MediaType.GITHUB,
                images=[],
                metadata={"error": str(e)},
            )

    async def _extract_repository(self, owner: str, repo: str, url: str) -> ExtractionResult:
        """Extract full repository content.

        Args:
            owner: Repository owner
            repo: Repository name
            url: Original URL

        Returns:
            Extraction result
        """
        # Get repository metadata
        repo_url = f"https://api.github.com/repos/{owner}/{repo}"
        repo_data = await self._api_request(repo_url)

        # Get default branch
        default_branch = repo_data.get("default_branch", "main")

        # Get README
        readme_content = await self._get_readme(owner, repo)

        # Get repository tree (file listing)
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
        try:
            tree_data = await self._api_request(tree_url)
            files = tree_data.get("tree", [])
        except Exception:
            files = []

        # Build markdown
        markdown_parts = []

        # Header with repo info
        markdown_parts.append(f"# {repo_data.get('full_name', f'{owner}/{repo}')}")
        markdown_parts.append("")

        if repo_data.get("description"):
            markdown_parts.append(f"> {repo_data['description']}")
            markdown_parts.append("")

        # Metadata
        markdown_parts.append("## Repository Info")
        markdown_parts.append("")
        markdown_parts.append(f"- **Owner:** {owner}")
        markdown_parts.append(f"- **Stars:** {repo_data.get('stargazers_count', 0):,}")
        markdown_parts.append(f"- **Forks:** {repo_data.get('forks_count', 0):,}")
        markdown_parts.append(f"- **Language:** {repo_data.get('language', 'N/A')}")
        markdown_parts.append(f"- **License:** {repo_data.get('license', {}).get('name', 'N/A') if repo_data.get('license') else 'N/A'}")
        markdown_parts.append(f"- **Default Branch:** {default_branch}")
        markdown_parts.append(f"- **URL:** {url}")
        markdown_parts.append("")

        # Topics/tags
        topics = repo_data.get("topics", [])
        if topics:
            markdown_parts.append(f"**Topics:** {', '.join(topics)}")
            markdown_parts.append("")

        # README
        if readme_content:
            markdown_parts.append("## README")
            markdown_parts.append("")
            markdown_parts.append(readme_content)
            markdown_parts.append("")

        # File tree
        if files:
            markdown_parts.append("## File Structure")
            markdown_parts.append("")
            markdown_parts.append("```")
            file_count = 0
            for item in files:
                if item.get("type") == "blob" and file_count < 100:
                    markdown_parts.append(item.get("path", ""))
                    file_count += 1
            if len([f for f in files if f.get("type") == "blob"]) > 100:
                markdown_parts.append(f"... and {len([f for f in files if f.get('type') == 'blob']) - 100} more files")
            markdown_parts.append("```")
            markdown_parts.append("")

        # Extract important files
        if self.include_code and files:
            markdown_parts.append("## Key Files")
            markdown_parts.append("")

            extracted_count = 0
            for item in files:
                if extracted_count >= self.max_files:
                    break

                if item.get("type") != "blob":
                    continue

                path = item.get("path", "")
                filename = path.split("/")[-1].lower()
                ext = "." + filename.split(".")[-1] if "." in filename else ""

                # Check if it's an important file or has a code extension
                is_important = filename in self.IMPORTANT_FILES
                is_code = ext in self.CODE_EXTENSIONS

                if is_important or is_code:
                    size = item.get("size", 0)
                    if size <= self.max_file_size:
                        try:
                            content = await self._get_file_content(owner, repo, default_branch, path)
                            if content:
                                markdown_parts.append(f"### {path}")
                                markdown_parts.append("")
                                lang = self._get_language(path)
                                markdown_parts.append(f"```{lang}")
                                markdown_parts.append(content)
                                markdown_parts.append("```")
                                markdown_parts.append("")
                                extracted_count += 1
                        except Exception:
                            pass

        markdown = "\n".join(markdown_parts)

        return ExtractionResult(
            markdown=markdown,
            title=repo_data.get("full_name", f"{owner}/{repo}"),
            source=url,
            media_type=MediaType.GITHUB,
            images=[],
            metadata={
                "owner": owner,
                "repo": repo,
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "language": repo_data.get("language"),
                "default_branch": default_branch,
                "description": repo_data.get("description"),
            },
        )

    async def _extract_file(
        self, owner: str, repo: str, branch: str, path: str, url: str
    ) -> ExtractionResult:
        """Extract a single file from GitHub.

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name
            path: File path
            url: Original URL

        Returns:
            Extraction result
        """
        content = await self._get_file_content(owner, repo, branch, path)

        if content is None:
            content = "*File content could not be retrieved*"

        filename = path.split("/")[-1]
        lang = self._get_language(path)

        markdown_parts = [
            f"# {filename}",
            "",
            f"**Repository:** {owner}/{repo}",
            f"**Branch:** {branch}",
            f"**Path:** {path}",
            f"**URL:** {url}",
            "",
            "## Content",
            "",
            f"```{lang}",
            content,
            "```",
        ]

        return ExtractionResult(
            markdown="\n".join(markdown_parts),
            title=filename,
            source=url,
            media_type=MediaType.GITHUB,
            images=[],
            metadata={
                "owner": owner,
                "repo": repo,
                "branch": branch,
                "path": path,
                "filename": filename,
            },
        )

    async def _extract_directory(
        self, owner: str, repo: str, branch: str, path: str, url: str
    ) -> ExtractionResult:
        """Extract a directory from GitHub.

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name
            path: Directory path
            url: Original URL

        Returns:
            Extraction result
        """
        # Get directory contents
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
        contents = await self._api_request(api_url)

        markdown_parts = [
            f"# {path or repo}",
            "",
            f"**Repository:** {owner}/{repo}",
            f"**Branch:** {branch}",
            f"**Path:** {path or '/'}",
            f"**URL:** {url}",
            "",
            "## Contents",
            "",
        ]

        # List files and directories
        dirs = [item for item in contents if item.get("type") == "dir"]
        files = [item for item in contents if item.get("type") == "file"]

        if dirs:
            markdown_parts.append("### Directories")
            markdown_parts.append("")
            for d in dirs:
                markdown_parts.append(f"- 📁 {d.get('name', '')}/")
            markdown_parts.append("")

        if files:
            markdown_parts.append("### Files")
            markdown_parts.append("")
            for f in files:
                size = f.get("size", 0)
                size_str = f"{size:,} bytes" if size < 1024 else f"{size/1024:.1f} KB"
                markdown_parts.append(f"- 📄 {f.get('name', '')} ({size_str})")
            markdown_parts.append("")

        # Extract file contents
        if self.include_code:
            markdown_parts.append("## File Contents")
            markdown_parts.append("")

            extracted_count = 0
            for item in files:
                if extracted_count >= self.max_files:
                    break

                name = item.get("name", "")
                size = item.get("size", 0)
                file_path = item.get("path", "")

                filename_lower = name.lower()
                ext = "." + filename_lower.split(".")[-1] if "." in filename_lower else ""

                is_important = filename_lower in self.IMPORTANT_FILES
                is_code = ext in self.CODE_EXTENSIONS

                if (is_important or is_code) and size <= self.max_file_size:
                    try:
                        content = await self._get_file_content(owner, repo, branch, file_path)
                        if content:
                            markdown_parts.append(f"### {name}")
                            markdown_parts.append("")
                            lang = self._get_language(name)
                            markdown_parts.append(f"```{lang}")
                            markdown_parts.append(content)
                            markdown_parts.append("```")
                            markdown_parts.append("")
                            extracted_count += 1
                    except Exception:
                        pass

        return ExtractionResult(
            markdown="\n".join(markdown_parts),
            title=path or repo,
            source=url,
            media_type=MediaType.GITHUB,
            images=[],
            metadata={
                "owner": owner,
                "repo": repo,
                "branch": branch,
                "path": path,
                "file_count": len(files),
                "dir_count": len(dirs),
            },
        )

    async def _get_readme(self, owner: str, repo: str) -> Optional[str]:
        """Get repository README content.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            README content or None
        """
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/readme"
            data = await self._api_request(url)

            if data.get("content"):
                content = base64.b64decode(data["content"]).decode("utf-8")
                return content
        except Exception:
            pass
        return None

    async def _get_file_content(
        self, owner: str, repo: str, branch: str, path: str
    ) -> Optional[str]:
        """Get file content from GitHub.

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name
            path: File path

        Returns:
            File content or None
        """
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
            data = await self._api_request(url)

            if data.get("content"):
                content = base64.b64decode(data["content"]).decode("utf-8")
                return content
        except Exception:
            pass
        return None

    def _get_language(self, path: str) -> str:
        """Get language identifier for syntax highlighting.

        Args:
            path: File path

        Returns:
            Language identifier
        """
        ext_to_lang = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "jsx",
            ".tsx": "tsx",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".r": "r",
            ".R": "r",
            ".sh": "bash",
            ".bash": "bash",
            ".zsh": "zsh",
            ".fish": "fish",
            ".ps1": "powershell",
            ".bat": "batch",
            ".cmd": "batch",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".sass": "sass",
            ".less": "less",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".xml": "xml",
            ".ini": "ini",
            ".cfg": "ini",
            ".conf": "ini",
            ".md": "markdown",
            ".rst": "rst",
            ".txt": "text",
            ".sql": "sql",
            ".graphql": "graphql",
            ".proto": "protobuf",
            ".dockerfile": "dockerfile",
            ".makefile": "makefile",
            ".cmake": "cmake",
        }

        filename = path.split("/")[-1].lower()

        # Check for special filenames
        if filename == "dockerfile":
            return "dockerfile"
        if filename == "makefile":
            return "makefile"
        if filename.startswith("."):
            return "text"

        # Check extension
        ext = "." + filename.split(".")[-1] if "." in filename else ""
        return ext_to_lang.get(ext, "text")

    def supports(self, source: Union[str, Path]) -> bool:
        """Check if this extractor handles the source.

        Args:
            source: Source to check

        Returns:
            True if this is a GitHub URL
        """
        source_str = str(source)

        if not source_str.startswith(("http://", "https://")):
            return False

        parsed = urlparse(source_str)
        return parsed.netloc in ("github.com", "www.github.com")
