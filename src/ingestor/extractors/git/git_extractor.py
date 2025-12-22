"""Unified Git repository extractor with GitHub API support.

Handles:
- Full git repository cloning (any server: GitHub, GitLab, Bitbucket, etc.)
- GitHub API for specific files/directories
- SSH and HTTPS authentication
- Bulk cloning via .download_git files
- Shallow clones, branches, tags, commits
- Submodule support
"""

import asyncio
import base64
import fnmatch
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import urlparse

from ...types import ExtractionResult, ExtractedImage, MediaType
from ..base import BaseExtractor


@dataclass
class GitRepoConfig:
    """Configuration for git repository extraction."""

    # Clone options
    shallow: bool = True  # Use shallow clone (--depth 1)
    depth: int = 1  # Clone depth for shallow clone
    branch: Optional[str] = None  # Specific branch to clone
    tag: Optional[str] = None  # Specific tag to clone
    commit: Optional[str] = None  # Specific commit to checkout

    # File filtering
    include_extensions: Set[str] = field(default_factory=lambda: {
        # Source code
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h", ".hpp",
        ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala", ".r", ".R",
        ".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd",
        # Web
        ".html", ".css", ".scss", ".sass", ".less", ".vue", ".svelte",
        # Config & data
        ".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".cfg", ".conf", ".env.example",
        # Documentation
        ".md", ".rst", ".txt", ".markdown", ".adoc", ".asciidoc",
        # Other
        ".sql", ".graphql", ".proto", ".dockerfile",
        ".makefile", ".cmake", ".gradle", ".maven",
    })

    exclude_patterns: Set[str] = field(default_factory=lambda: {
        # Directories
        "node_modules/", "vendor/", "venv/", ".venv/", "__pycache__/",
        ".git/", ".svn/", ".hg/", "dist/", "build/", "target/",
        "coverage/", ".coverage/", ".pytest_cache/", ".mypy_cache/",
        ".tox/", "eggs/", "*.egg-info/",
        # Files
        "*.min.js", "*.min.css", "*.map",
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
        "Cargo.lock", "poetry.lock", "Pipfile.lock",
    })

    # Processing options
    max_file_size: int = 500_000  # 500KB max per file
    max_total_files: int = 500  # Maximum files to process
    include_binary_metadata: bool = False  # Extract metadata from binary files
    include_submodules: bool = False  # Process git submodules

    # Important files to always include
    important_files: Set[str] = field(default_factory=lambda: {
        "readme.md", "readme.rst", "readme.txt", "readme",
        "license", "license.md", "license.txt", "mit-license", "apache-license",
        "contributing.md", "contributing", "contribute.md",
        "changelog.md", "changelog", "changes.md", "history.md", "news.md",
        "code_of_conduct.md", "security.md",
        "requirements.txt", "setup.py", "pyproject.toml", "setup.cfg", "manifest.in",
        "package.json", "tsconfig.json", "webpack.config.js", "vite.config.js",
        "cargo.toml", "go.mod", "go.sum", "gemfile", "composer.json",
        "makefile", "dockerfile", "docker-compose.yml", "docker-compose.yaml",
        ".gitignore", ".env.example", ".editorconfig",
    })


class GitExtractor(BaseExtractor):
    """Unified extractor for git repositories and GitHub URLs.

    Supports:
    - Full repository cloning from any git server
    - GitHub API for specific files/directories (github.com only)
    - HTTPS URLs (https://github.com/user/repo.git)
    - SSH URLs (git@github.com:user/repo.git)
    - Git protocol URLs (git://github.com/user/repo.git)
    - Local repository paths
    - Private repositories (via SSH keys or tokens)
    - Shallow cloning for large repos
    - Branch/tag/commit specific cloning
    - Submodule support
    - Bulk cloning via .download_git files
    """

    media_type = MediaType.GIT

    # Git URL patterns for clone
    GIT_URL_PATTERNS = [
        r"^https?://[^/]+/[^/]+/[^/]+(?:\.git)?/?$",  # HTTPS repo root
        r"^git@[^:]+:[^/]+/[^/]+(?:\.git)?$",  # SSH
        r"^git://[^/]+/[^/]+/[^/]+(?:\.git)?$",  # Git protocol
        r"^ssh://git@[^/]+/[^/]+/[^/]+(?:\.git)?$",  # SSH with ssh://
    ]

    # GitHub-specific URL patterns (for API access)
    GITHUB_PATTERNS = {
        "repo": r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/?$",
        "file": r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)$",
        "tree": r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/tree/([^/]+)/?(.*)$",
        "raw": r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/raw/([^/]+)/(.+)$",
    }

    # Binary file extensions to skip content extraction
    BINARY_EXTENSIONS = {
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".bmp", ".tiff",
        ".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac",
        ".mp4", ".avi", ".mov", ".mkv", ".webm",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
        ".exe", ".dll", ".so", ".dylib", ".a", ".o", ".pyc", ".pyo",
        ".woff", ".woff2", ".ttf", ".eot", ".otf",
        ".db", ".sqlite", ".sqlite3",
    }

    def __init__(
        self,
        config: Optional[GitRepoConfig] = None,
        token: Optional[str] = None,
        registry: Optional[Any] = None,
        use_api_for_github: bool = True,  # Use GitHub API when possible
    ):
        """Initialize git extractor.

        Args:
            config: Repository extraction configuration
            token: Git/GitHub token for private repositories
            registry: Extractor registry for processing extracted files
            use_api_for_github: Use GitHub API for github.com URLs (faster for single files)
        """
        self.config = config or GitRepoConfig()
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GIT_TOKEN")
        self._registry = registry
        self.use_api_for_github = use_api_for_github

    def set_registry(self, registry: Any):
        """Set the extractor registry."""
        self._registry = registry

    def supports(self, source: Union[str, Path]) -> bool:
        """Check if this extractor can handle the source."""
        source_str = str(source)

        # Check for .download_git file
        if source_str.endswith(".download_git"):
            return True

        # Check for local git repository
        path = Path(source_str)
        if path.exists():
            git_dir = path / ".git"
            return git_dir.exists() and git_dir.is_dir()

        # Check GitHub URL patterns (file, tree, repo)
        for pattern in self.GITHUB_PATTERNS.values():
            if re.match(pattern, source_str, re.IGNORECASE):
                return True

        # Check git URL patterns
        for pattern in self.GIT_URL_PATTERNS:
            if re.match(pattern, source_str, re.IGNORECASE):
                return True

        return False

    async def extract(self, source: Union[str, Path]) -> ExtractionResult:
        """Extract content from a git repository or GitHub URL."""
        source_str = str(source)

        # Handle .download_git files
        if source_str.endswith(".download_git"):
            return await self._process_download_git_file(Path(source_str))

        # Handle local repositories
        path = Path(source_str)
        if path.exists() and (path / ".git").exists():
            return await self._extract_from_local_repo(path, source_str)

        # Check if it's a GitHub URL that can use API
        github_parsed = self._parse_github_url(source_str)
        if github_parsed and self.use_api_for_github:
            url_type = github_parsed["url_type"]
            
            # For single files and directories, use GitHub API (faster)
            if url_type in ("file", "tree", "raw"):
                return await self._extract_via_github_api(github_parsed, source_str)
            
            # For full repo, clone is more comprehensive
            # But we can still get metadata via API
            if url_type == "repo":
                return await self._extract_github_repo_hybrid(github_parsed, source_str)

        # For all other URLs, clone the repository
        return await self._extract_from_remote_repo(source_str)

    # ==================== GitHub API Methods ====================

    def _parse_github_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse a GitHub URL to extract components."""
        url = str(url).rstrip("/")

        # Repository root
        match = re.match(self.GITHUB_PATTERNS["repo"], url)
        if match:
            return {
                "owner": match.group(1),
                "repo": match.group(2),
                "branch": None,
                "path": "",
                "url_type": "repo",
            }

        # File
        match = re.match(self.GITHUB_PATTERNS["file"], url)
        if match:
            return {
                "owner": match.group(1),
                "repo": match.group(2),
                "branch": match.group(3),
                "path": match.group(4),
                "url_type": "file",
            }

        # Directory
        match = re.match(self.GITHUB_PATTERNS["tree"], url)
        if match:
            return {
                "owner": match.group(1),
                "repo": match.group(2),
                "branch": match.group(3),
                "path": match.group(4),
                "url_type": "tree",
            }

        # Raw file
        match = re.match(self.GITHUB_PATTERNS["raw"], url)
        if match:
            return {
                "owner": match.group(1),
                "repo": match.group(2),
                "branch": match.group(3),
                "path": match.group(4),
                "url_type": "raw",
            }

        return None

    def _get_api_headers(self) -> dict:
        """Get HTTP headers for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Ingestor/1.0",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    async def _api_request(self, url: str) -> dict:
        """Make a request to GitHub API."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._get_api_headers(), timeout=30.0)
            response.raise_for_status()
            return response.json()

    async def _extract_via_github_api(
        self, parsed: Dict[str, Any], url: str
    ) -> ExtractionResult:
        """Extract content using GitHub API (for files/directories)."""
        owner = parsed["owner"]
        repo = parsed["repo"]
        branch = parsed["branch"]
        path = parsed["path"]
        url_type = parsed["url_type"]

        try:
            if url_type == "file" or url_type == "raw":
                return await self._extract_github_file(owner, repo, branch, path, url)
            elif url_type == "tree":
                return await self._extract_github_directory(owner, repo, branch, path, url)
        except Exception as e:
            return ExtractionResult(
                markdown=f"# Error\n\nFailed to extract from GitHub: {url}\n\n{str(e)}",
                title="Error",
                source=url,
                media_type=MediaType.GIT,
                images=[],
                metadata={"error": str(e)},
            )

    async def _extract_github_file(
        self, owner: str, repo: str, branch: str, path: str, url: str
    ) -> ExtractionResult:
        """Extract a single file via GitHub API."""
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
        data = await self._api_request(api_url)

        content = "*File content could not be retrieved*"
        if data.get("content"):
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")

        filename = path.split("/")[-1]
        lang = self._detect_language(Path(filename))

        markdown = "\n".join([
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
        ])

        return ExtractionResult(
            markdown=markdown,
            title=filename,
            source=url,
            media_type=MediaType.GIT,
            images=[],
            metadata={
                "owner": owner,
                "repo": repo,
                "branch": branch,
                "path": path,
                "filename": filename,
                "extraction_method": "github_api",
            },
        )

    async def _extract_github_directory(
        self, owner: str, repo: str, branch: str, path: str, url: str
    ) -> ExtractionResult:
        """Extract a directory via GitHub API."""
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
        markdown_parts.append("## File Contents")
        markdown_parts.append("")

        extracted_count = 0
        for item in files:
            if extracted_count >= self.config.max_total_files:
                break

            name = item.get("name", "")
            size = item.get("size", 0)
            file_path = item.get("path", "")
            ext = Path(name).suffix.lower()

            is_important = name.lower() in self.config.important_files
            is_code = ext in self.config.include_extensions

            if (is_important or is_code) and size <= self.config.max_file_size:
                try:
                    file_api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={branch}"
                    file_data = await self._api_request(file_api_url)
                    if file_data.get("content"):
                        content = base64.b64decode(file_data["content"]).decode("utf-8", errors="replace")
                        lang = self._detect_language(Path(name))
                        markdown_parts.extend([
                            f"### {name}",
                            "",
                            f"```{lang}",
                            content,
                            "```",
                            "",
                        ])
                        extracted_count += 1
                except Exception:
                    pass

        return ExtractionResult(
            markdown="\n".join(markdown_parts),
            title=path or repo,
            source=url,
            media_type=MediaType.GIT,
            images=[],
            metadata={
                "owner": owner,
                "repo": repo,
                "branch": branch,
                "path": path,
                "file_count": len(files),
                "dir_count": len(dirs),
                "extraction_method": "github_api",
            },
        )

    async def _extract_github_repo_hybrid(
        self, parsed: Dict[str, Any], url: str
    ) -> ExtractionResult:
        """Extract GitHub repo using clone + API for metadata."""
        owner = parsed["owner"]
        repo = parsed["repo"]

        # Get GitHub-specific metadata via API
        github_metadata = {}
        try:
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            repo_data = await self._api_request(api_url)
            github_metadata = {
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "watchers": repo_data.get("watchers_count", 0),
                "language": repo_data.get("language"),
                "topics": repo_data.get("topics", []),
                "description": repo_data.get("description"),
                "license": repo_data.get("license", {}).get("name") if repo_data.get("license") else None,
                "open_issues": repo_data.get("open_issues_count", 0),
                "created_at": repo_data.get("created_at"),
                "updated_at": repo_data.get("updated_at"),
            }
        except Exception:
            pass

        # Clone the repository
        result = await self._extract_from_remote_repo(url)

        # Merge GitHub metadata into result
        if github_metadata:
            result.metadata.update(github_metadata)

            # Add GitHub stats to markdown
            if result.markdown and "## Repository Info" in result.markdown:
                stats_lines = []
                if github_metadata.get("stars"):
                    stats_lines.append(f"- **Stars:** {github_metadata['stars']:,}")
                if github_metadata.get("forks"):
                    stats_lines.append(f"- **Forks:** {github_metadata['forks']:,}")
                if github_metadata.get("language"):
                    stats_lines.append(f"- **Language:** {github_metadata['language']}")
                if github_metadata.get("license"):
                    stats_lines.append(f"- **License:** {github_metadata['license']}")
                if github_metadata.get("topics"):
                    stats_lines.append(f"- **Topics:** {', '.join(github_metadata['topics'])}")
                if github_metadata.get("description"):
                    # Add description after title
                    result.markdown = result.markdown.replace(
                        "\n\n## Repository Info",
                        f"\n\n> {github_metadata['description']}\n\n## Repository Info"
                    )

                if stats_lines:
                    stats_text = "\n".join(stats_lines)
                    result.markdown = result.markdown.replace(
                        "## Repository Info\n\n",
                        f"## Repository Info\n\n{stats_text}\n"
                    )

        return result

    # ==================== Git Clone Methods ====================

    async def _process_download_git_file(self, file_path: Path) -> ExtractionResult:
        """Process a .download_git file containing repository URLs."""
        repos: List[str] = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        repos.append(line)
        except Exception as e:
            return ExtractionResult(
                markdown=f"# Error\n\nFailed to read .download_git file: {e}",
                title="Error",
                source=str(file_path),
                media_type=MediaType.GIT,
                images=[],
                metadata={"error": str(e)},
            )

        if not repos:
            return ExtractionResult(
                markdown="# Error\n\nNo repository URLs found in .download_git file",
                title="Error",
                source=str(file_path),
                media_type=MediaType.GIT,
                images=[],
                metadata={"error": "Empty file"},
            )

        # Process each repository
        results: List[ExtractionResult] = []
        for repo_url in repos:
            try:
                result = await self.extract(repo_url)
                results.append(result)
            except Exception as e:
                results.append(ExtractionResult(
                    markdown=f"# Error\n\nFailed to process {repo_url}: {e}",
                    title="Error",
                    source=repo_url,
                    media_type=MediaType.GIT,
                    images=[],
                    metadata={"error": str(e)},
                ))

        return self._combine_results(results, file_path)

    def _combine_results(
        self, results: List[ExtractionResult], source_file: Path
    ) -> ExtractionResult:
        """Combine multiple extraction results into one."""
        all_markdown = [
            f"# Bulk Git Repository Extraction",
            "",
            f"**Source:** `{source_file.name}`",
            f"**Repositories:** {len(results)}",
            f"**Processed:** {datetime.now().isoformat()}",
            "",
            "---",
            "",
        ]

        all_images: List[ExtractedImage] = []
        total_files = 0
        failed = 0

        for result in results:
            all_markdown.append(result.markdown)
            all_markdown.append("")
            all_markdown.append("---")
            all_markdown.append("")
            all_images.extend(result.images)
            total_files += result.metadata.get("file_count", 0)
            if "error" in result.metadata:
                failed += 1

        return ExtractionResult(
            markdown="\n".join(all_markdown),
            title=f"Bulk: {source_file.stem}",
            source=str(source_file),
            media_type=MediaType.GIT,
            images=all_images,
            metadata={
                "repos_total": len(results),
                "repos_failed": failed,
                "total_files": total_files,
            },
        )

    async def _extract_from_remote_repo(self, url: str) -> ExtractionResult:
        """Clone and extract from a remote repository."""
        repo_name = self._parse_repo_name(url)

        with tempfile.TemporaryDirectory() as tmpdir:
            clone_path = Path(tmpdir) / repo_name

            try:
                await self._clone_repo(url, clone_path)
            except Exception as e:
                return ExtractionResult(
                    markdown=f"# Error\n\nFailed to clone repository: {url}\n\n```\n{e}\n```",
                    title=f"Error: {repo_name}",
                    source=url,
                    media_type=MediaType.GIT,
                    images=[],
                    metadata={"error": str(e), "url": url},
                )

            return await self._extract_from_local_repo(clone_path, url)

    async def _clone_repo(self, url: str, target_path: Path) -> None:
        """Clone a git repository."""
        cmd = ["git", "clone"]

        # Add authentication for HTTPS URLs if token is available
        clone_url = url
        if self.token and url.startswith("https://"):
            parsed = url.replace("https://", f"https://{self.token}@")
            clone_url = parsed

        # Shallow clone options
        if self.config.shallow:
            cmd.extend(["--depth", str(self.config.depth)])

        # Branch/tag options
        if self.config.branch:
            cmd.extend(["--branch", self.config.branch])
        elif self.config.tag:
            cmd.extend(["--branch", self.config.tag])

        # Single branch for efficiency
        if self.config.shallow:
            cmd.append("--single-branch")

        # Submodules
        if self.config.include_submodules:
            cmd.append("--recurse-submodules")

        cmd.extend([clone_url, str(target_path)])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace")
            if self.token:
                error_msg = error_msg.replace(self.token, "[TOKEN]")
            raise Exception(f"Git clone failed: {error_msg}")

        # Checkout specific commit if requested
        if self.config.commit:
            checkout_process = await asyncio.create_subprocess_exec(
                "git", "-C", str(target_path), "checkout", self.config.commit,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            checkout_stdout, checkout_stderr = await checkout_process.communicate()

            if checkout_process.returncode != 0:
                error_msg = checkout_stderr.decode("utf-8", errors="replace")
                if self.token:
                    error_msg = error_msg.replace(self.token, "[TOKEN]")
                raise Exception(
                    f"Git checkout failed for commit '{self.config.commit}': {error_msg}"
                )

    async def _extract_from_local_repo(
        self, repo_path: Path, source: str
    ) -> ExtractionResult:
        """Extract content from a local git repository."""
        repo_name = repo_path.name

        metadata = await self._get_repo_metadata(repo_path)
        metadata["source"] = source

        structure = self._build_directory_tree(repo_path)
        files_content, images = await self._process_files(repo_path)

        markdown = self._build_markdown(
            repo_name=repo_name,
            metadata=metadata,
            structure=structure,
            files=files_content,
            source=source,
        )

        return ExtractionResult(
            markdown=markdown,
            title=repo_name,
            source=source,
            media_type=MediaType.GIT,
            images=images,
            metadata=metadata,
        )

    async def _get_repo_metadata(self, repo_path: Path) -> Dict[str, Any]:
        """Get repository metadata from git."""
        metadata: Dict[str, Any] = {
            "name": repo_path.name,
            "extracted_at": datetime.now().isoformat(),
        }

        try:
            # Get remote URL
            result = subprocess.run(
                ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                remote_url = result.stdout.strip()
                if self.token and self.token in remote_url:
                    remote_url = remote_url.replace(self.token + "@", "")
                metadata["remote_url"] = remote_url

            # Get current branch
            result = subprocess.run(
                ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                metadata["branch"] = result.stdout.strip()

            # Get current commit
            result = subprocess.run(
                ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                metadata["commit"] = result.stdout.strip()

            # Get last commit date
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "-1", "--format=%ci"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                metadata["last_commit_date"] = result.stdout.strip()

            # Get commit count
            result = subprocess.run(
                ["git", "-C", str(repo_path), "rev-list", "--count", "HEAD"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                metadata["commit_count"] = int(result.stdout.strip())

        except Exception:
            pass

        return metadata

    def _build_directory_tree(self, repo_path: Path, max_depth: int = 4) -> str:
        """Build a text representation of the directory structure."""
        lines = [repo_path.name + "/"]

        def add_tree(path: Path, prefix: str = "", depth: int = 0):
            if depth >= max_depth:
                return

            try:
                entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            except PermissionError:
                return

            filtered = []
            for entry in entries:
                name = entry.name
                if name == ".git":
                    continue
                if any(
                    pattern.rstrip("/") == name or
                    (pattern.endswith("/") and entry.is_dir() and name == pattern.rstrip("/"))
                    for pattern in self.config.exclude_patterns
                ):
                    continue
                filtered.append(entry)

            for i, entry in enumerate(filtered):
                is_last = i == len(filtered) - 1
                connector = "└── " if is_last else "├── "
                next_prefix = prefix + ("    " if is_last else "│   ")

                if entry.is_dir():
                    lines.append(f"{prefix}{connector}{entry.name}/")
                    add_tree(entry, next_prefix, depth + 1)
                else:
                    lines.append(f"{prefix}{connector}{entry.name}")

        add_tree(repo_path)

        if len(lines) > 200:
            lines = lines[:200]
            lines.append("... (truncated)")

        return "\n".join(lines)

    async def _process_files(
        self, repo_path: Path
    ) -> tuple[List[Dict[str, Any]], List[ExtractedImage]]:
        """Process all files in the repository."""
        files_content: List[Dict[str, Any]] = []
        images: List[ExtractedImage] = []
        processed_count = 0

        all_files: List[Path] = []
        for file_path in repo_path.rglob("*"):
            if not file_path.is_file():
                continue

            if ".git" in file_path.parts:
                continue

            rel_path = file_path.relative_to(repo_path)
            rel_path_str = str(rel_path)

            skip = False
            for pattern in self.config.exclude_patterns:
                if pattern.endswith("/"):
                    if pattern.rstrip("/") in rel_path.parts:
                        skip = True
                        break
                elif "*" in pattern:
                    if fnmatch.fnmatch(rel_path_str, pattern):
                        skip = True
                        break
                    if fnmatch.fnmatch(file_path.name, pattern):
                        skip = True
                        break
                else:
                    if file_path.name == pattern:
                        skip = True
                        break

            if skip:
                continue

            all_files.append(file_path)

        def file_sort_key(f: Path) -> tuple:
            name_lower = f.name.lower()
            is_important = name_lower in self.config.important_files
            is_readme = name_lower.startswith("readme")
            return (not is_readme, not is_important, str(f.relative_to(repo_path)))

        all_files.sort(key=file_sort_key)

        for file_path in all_files:
            if processed_count >= self.config.max_total_files:
                break

            rel_path = file_path.relative_to(repo_path)
            ext = file_path.suffix.lower()
            name_lower = file_path.name.lower()

            is_important = name_lower in self.config.important_files
            is_included_ext = ext in self.config.include_extensions
            is_no_ext_text = ext == "" and name_lower in {
                "license", "readme", "changelog", "contributing", "makefile", "dockerfile"
            }

            if not (is_important or is_included_ext or is_no_ext_text):
                if self.config.include_binary_metadata and ext in self.BINARY_EXTENSIONS:
                    files_content.append({
                        "path": str(rel_path),
                        "type": "binary",
                        "size": file_path.stat().st_size,
                        "extension": ext,
                    })
                continue

            try:
                file_size = file_path.stat().st_size
                if file_size > self.config.max_file_size:
                    files_content.append({
                        "path": str(rel_path),
                        "type": "skipped",
                        "reason": f"File too large ({file_size:,} bytes)",
                        "size": file_size,
                    })
                    continue
            except Exception:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                lang = self._detect_language(file_path)

                files_content.append({
                    "path": str(rel_path),
                    "type": "text",
                    "language": lang,
                    "content": content,
                    "size": file_size,
                })
                processed_count += 1
            except Exception as e:
                files_content.append({
                    "path": str(rel_path),
                    "type": "error",
                    "error": str(e),
                })

        return files_content, images

    def _detect_language(self, file_path: Path) -> str:
        """Detect the programming language for syntax highlighting."""
        ext_to_lang = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".jsx": "jsx", ".tsx": "tsx", ".java": "java",
            ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp",
            ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
            ".swift": "swift", ".kt": "kotlin", ".scala": "scala",
            ".r": "r", ".R": "r",
            ".sh": "bash", ".bash": "bash", ".zsh": "zsh", ".fish": "fish",
            ".ps1": "powershell", ".bat": "batch", ".cmd": "batch",
            ".html": "html", ".css": "css", ".scss": "scss", ".sass": "sass", ".less": "less",
            ".vue": "vue", ".svelte": "svelte",
            ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
            ".xml": "xml", ".ini": "ini", ".cfg": "ini", ".conf": "conf",
            ".md": "markdown", ".rst": "rst",
            ".sql": "sql", ".graphql": "graphql", ".proto": "protobuf",
            ".dockerfile": "dockerfile", ".makefile": "makefile", ".cmake": "cmake",
            ".gradle": "gradle",
        }

        name_lower = file_path.name.lower()
        if name_lower == "dockerfile":
            return "dockerfile"
        if name_lower == "makefile":
            return "makefile"
        if name_lower in {"gemfile", "rakefile"}:
            return "ruby"

        return ext_to_lang.get(file_path.suffix.lower(), "")

    def _build_markdown(
        self,
        repo_name: str,
        metadata: Dict[str, Any],
        structure: str,
        files: List[Dict[str, Any]],
        source: str,
    ) -> str:
        """Build the final markdown document."""
        lines = [f"# {repo_name}", ""]

        lines.extend(["## Repository Info", ""])
        lines.append(f"- **Source:** `{source}`")

        if metadata.get("branch"):
            lines.append(f"- **Branch:** `{metadata['branch']}`")
        if metadata.get("commit"):
            lines.append(f"- **Commit:** `{metadata['commit'][:12]}`")
        if metadata.get("last_commit_date"):
            lines.append(f"- **Last Commit:** {metadata['last_commit_date']}")
        if metadata.get("commit_count"):
            lines.append(f"- **Commits:** {metadata['commit_count']:,}")

        lines.append(f"- **Extracted:** {metadata.get('extracted_at', 'N/A')}")
        lines.extend(["", ""])

        lines.extend([
            "## Directory Structure", "",
            "```", structure, "```", "",
        ])

        text_files = [f for f in files if f.get("type") == "text"]
        skipped_files = [f for f in files if f.get("type") == "skipped"]
        binary_files = [f for f in files if f.get("type") == "binary"]

        lines.extend([
            "## File Statistics", "",
            f"- **Files Processed:** {len(text_files)}",
            f"- **Files Skipped:** {len(skipped_files)}",
        ])
        if binary_files:
            lines.append(f"- **Binary Files:** {len(binary_files)}")
        lines.extend(["", ""])

        readme_files = [f for f in text_files if f["path"].lower().startswith("readme")]
        if readme_files:
            readme = readme_files[0]
            lines.extend(["## README", "", readme["content"], ""])

        code_files = [f for f in text_files if not f["path"].lower().startswith("readme")]
        if code_files:
            lines.extend(["## Source Files", ""])

            for file_info in code_files:
                path = file_info["path"]
                lang = file_info.get("language", "")
                content = file_info["content"]

                lines.extend([
                    f"### `{path}`", "",
                    f"```{lang}", content.rstrip(), "```", "",
                ])

        if skipped_files:
            lines.extend([
                "## Skipped Files", "",
                "The following files were skipped due to size limits:", "",
            ])
            for f in skipped_files[:20]:
                lines.append(f"- `{f['path']}` ({f.get('reason', 'Unknown')})")
            if len(skipped_files) > 20:
                lines.append(f"- ... and {len(skipped_files) - 20} more")
            lines.append("")

        metadata["file_count"] = len(text_files)
        metadata["skipped_count"] = len(skipped_files)
        metadata["binary_count"] = len(binary_files)

        return "\n".join(lines)

    def _parse_repo_name(self, url: str) -> str:
        """Parse repository name from URL."""
        url = url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]

        if ":" in url and "@" in url:
            name = url.split(":")[-1].split("/")[-1]
        else:
            name = url.split("/")[-1]

        return name or "repository"


# Helper function
def parse_download_git_file(path: Path) -> List[str]:
    """Parse a .download_git file to get repository URLs."""
    urls: List[str] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)
    except Exception:
        pass
    return urls
