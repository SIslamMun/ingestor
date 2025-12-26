"""File type detection using Google's Magika (AI-powered, 99% accuracy)."""

from pathlib import Path
from typing import Optional, Union
import re

from magika import Magika

from ..types import MediaType


class FileDetector:
    """Detect file types using Google's Magika AI model.

    Magika provides 99% accuracy for file type detection by analyzing
    file content rather than just extensions.
    """

    # Map Magika labels to our MediaType enum
    MAGIKA_TO_MEDIA_TYPE: dict[str, MediaType] = {
        # Documents
        "pdf": MediaType.PDF,
        "docx": MediaType.DOCX,
        "doc": MediaType.DOCX,  # Legacy Word
        "pptx": MediaType.PPTX,
        "ppt": MediaType.PPTX,  # Legacy PowerPoint
        "epub": MediaType.EPUB,
        # Spreadsheets
        "xlsx": MediaType.XLSX,
        "xls": MediaType.XLS,
        "csv": MediaType.CSV,
        # Audio
        "mp3": MediaType.AUDIO,
        "wav": MediaType.AUDIO,
        "flac": MediaType.AUDIO,
        "ogg": MediaType.AUDIO,
        "m4a": MediaType.AUDIO,
        "aac": MediaType.AUDIO,
        # Data
        "json": MediaType.JSON,
        "xml": MediaType.XML,
        # Archives
        "zip": MediaType.ZIP,
        "gzip": MediaType.ZIP,
        "tar": MediaType.ZIP,
        # Images
        "png": MediaType.IMAGE,
        "jpeg": MediaType.IMAGE,
        "jpg": MediaType.IMAGE,
        "gif": MediaType.IMAGE,
        "webp": MediaType.IMAGE,
        "bmp": MediaType.IMAGE,
        "tiff": MediaType.IMAGE,
        "svg": MediaType.IMAGE,
        # Text (various text types map to TXT)
        "txt": MediaType.TXT,
        "text": MediaType.TXT,
        "markdown": MediaType.TXT,
        "rst": MediaType.TXT,
        "html": MediaType.TXT,  # Local HTML files treated as text
        # Code files (treat as text for extraction)
        "python": MediaType.TXT,
        "javascript": MediaType.TXT,
        "typescript": MediaType.TXT,
        "java": MediaType.TXT,
        "c": MediaType.TXT,
        "cpp": MediaType.TXT,
        "csharp": MediaType.TXT,
        "go": MediaType.TXT,
        "rust": MediaType.TXT,
        "ruby": MediaType.TXT,
        "php": MediaType.TXT,
        "shell": MediaType.TXT,
        "bash": MediaType.TXT,
        "powershell": MediaType.TXT,
        "sql": MediaType.TXT,
        "yaml": MediaType.TXT,
        "toml": MediaType.TXT,
        "ini": MediaType.TXT,
        "css": MediaType.TXT,
        "scss": MediaType.TXT,
        "less": MediaType.TXT,
        # Common misdetections that should be treated as text
        "autohotkey": MediaType.TXT,  # Large text files sometimes misdetected
        "perl": MediaType.TXT,
        "lua": MediaType.TXT,
        "r": MediaType.TXT,
        "scala": MediaType.TXT,
        "kotlin": MediaType.TXT,
        "swift": MediaType.TXT,
        "dart": MediaType.TXT,
    }

    # URL patterns for web content
    YOUTUBE_PATTERNS = [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+",
        r"(?:https?://)?(?:www\.)?youtu\.be/[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=[\w-]+",
    ]

    GITHUB_PATTERNS = [
        r"^https?://(?:www\.)?github\.com/[^/]+/[^/]+(?:/.*)?$",
    ]

    # Git repository URL patterns (for full clone)
    GIT_PATTERNS = [
        r"^git@[^:]+:[^/]+/[^/]+(?:\.git)?$",  # SSH: git@github.com:user/repo.git
        r"^git://[^/]+/[^/]+/[^/]+(?:\.git)?$",  # Git protocol
        r"^ssh://git@[^/]+/[^/]+/[^/]+(?:\.git)?$",  # SSH with ssh://
    ]

    WEB_PATTERN = r"^https?://"

    def __init__(self):
        """Initialize the file detector with Magika."""
        self._magika: Optional[Magika] = None

    @property
    def magika(self) -> Magika:
        """Lazy-load Magika instance."""
        if self._magika is None:
            self._magika = Magika()
        return self._magika

    def detect(self, source: Union[str, Path]) -> MediaType:
        """Detect the media type of a source.

        Args:
            source: File path or URL

        Returns:
            Detected MediaType
        """
        source_str = str(source)

        # Check for URLs first
        if self._is_youtube_url(source_str):
            return MediaType.YOUTUBE

        if self._is_github_url(source_str):
            return MediaType.GITHUB

        if self._is_git_url(source_str):
            return MediaType.GIT

        # Check for PDF URLs before generic web URLs
        if self._is_pdf_url(source_str):
            return MediaType.PDF

        if self._is_web_url(source_str):
            return MediaType.WEB

        # Check for .url files (contain URLs to crawl)
        if source_str.lower().endswith(".url"):
            return MediaType.WEB

        # Check for .download_git files (contain git repo URLs)
        if source_str.lower().endswith(".download_git"):
            return MediaType.GIT

        # For files, use Magika
        path = Path(source)
        if path.exists() and path.is_file():
            return self._detect_file(path)

        # Fallback to extension-based detection
        return self._detect_by_extension(path)

    def detect_bytes(self, data: bytes) -> MediaType:
        """Detect media type from raw bytes.

        Args:
            data: Raw file content

        Returns:
            Detected MediaType
        """
        result = self.magika.identify_bytes(data)
        label = result.output.label.lower()
        return self.MAGIKA_TO_MEDIA_TYPE.get(label, MediaType.UNKNOWN)

    def _detect_file(self, path: Path) -> MediaType:
        """Detect file type using Magika with extension-based fallback."""
        try:
            result = self.magika.identify_path(path)
            label = result.output.label.lower()
            detected = self.MAGIKA_TO_MEDIA_TYPE.get(label, MediaType.UNKNOWN)
            
            # If Magika returns UNKNOWN, try extension-based detection
            if detected == MediaType.UNKNOWN:
                return self._detect_by_extension(path)
            
            return detected
        except Exception:
            # Fallback to extension if Magika fails
            return self._detect_by_extension(path)

    def _detect_by_extension(self, path: Path) -> MediaType:
        """Fallback detection by file extension."""
        ext = path.suffix.lower().lstrip(".")
        extension_map = {
            # Documents
            "pdf": MediaType.PDF,
            "docx": MediaType.DOCX,
            "doc": MediaType.DOCX,
            "pptx": MediaType.PPTX,
            "ppt": MediaType.PPTX,
            "xlsx": MediaType.XLSX,
            "xls": MediaType.XLS,
            "csv": MediaType.CSV,
            "tsv": MediaType.CSV,
            "epub": MediaType.EPUB,
            # Audio
            "mp3": MediaType.AUDIO,
            "wav": MediaType.AUDIO,
            "flac": MediaType.AUDIO,
            "m4a": MediaType.AUDIO,
            "ogg": MediaType.AUDIO,
            "aac": MediaType.AUDIO,
            # Data
            "json": MediaType.JSON,
            "xml": MediaType.XML,
            # Archives
            "zip": MediaType.ZIP,
            "tar": MediaType.ZIP,
            "gz": MediaType.ZIP,
            "tgz": MediaType.ZIP,
            "rar": MediaType.ZIP,
            "7z": MediaType.ZIP,
            # Images
            "png": MediaType.IMAGE,
            "jpg": MediaType.IMAGE,
            "jpeg": MediaType.IMAGE,
            "gif": MediaType.IMAGE,
            "webp": MediaType.IMAGE,
            "bmp": MediaType.IMAGE,
            "tiff": MediaType.IMAGE,
            "svg": MediaType.IMAGE,
            "ico": MediaType.IMAGE,
            # Text/Plain text
            "txt": MediaType.TXT,
            "text": MediaType.TXT,
            "md": MediaType.TXT,
            "markdown": MediaType.TXT,
            "rst": MediaType.TXT,
            "html": MediaType.TXT,
            "htm": MediaType.TXT,
            "log": MediaType.TXT,
            "cfg": MediaType.TXT,
            "conf": MediaType.TXT,
            "ini": MediaType.TXT,
            # Code files (treated as text)
            "py": MediaType.TXT,
            "pyw": MediaType.TXT,
            "pyi": MediaType.TXT,
            "js": MediaType.TXT,
            "mjs": MediaType.TXT,
            "cjs": MediaType.TXT,
            "ts": MediaType.TXT,
            "tsx": MediaType.TXT,
            "jsx": MediaType.TXT,
            "java": MediaType.TXT,
            "c": MediaType.TXT,
            "h": MediaType.TXT,
            "cpp": MediaType.TXT,
            "hpp": MediaType.TXT,
            "cc": MediaType.TXT,
            "cxx": MediaType.TXT,
            "cs": MediaType.TXT,
            "go": MediaType.TXT,
            "rs": MediaType.TXT,
            "rb": MediaType.TXT,
            "php": MediaType.TXT,
            "sh": MediaType.TXT,
            "bash": MediaType.TXT,
            "zsh": MediaType.TXT,
            "ps1": MediaType.TXT,
            "sql": MediaType.TXT,
            "yaml": MediaType.TXT,
            "yml": MediaType.TXT,
            "toml": MediaType.TXT,
            "css": MediaType.TXT,
            "scss": MediaType.TXT,
            "less": MediaType.TXT,
            "sass": MediaType.TXT,
            "r": MediaType.TXT,
            "scala": MediaType.TXT,
            "kt": MediaType.TXT,
            "kts": MediaType.TXT,
            "swift": MediaType.TXT,
            "dart": MediaType.TXT,
            "lua": MediaType.TXT,
            "pl": MediaType.TXT,
            "pm": MediaType.TXT,
            "ex": MediaType.TXT,
            "exs": MediaType.TXT,
            "erl": MediaType.TXT,
            "hrl": MediaType.TXT,
            "clj": MediaType.TXT,
            "cljs": MediaType.TXT,
            "vue": MediaType.TXT,
            "svelte": MediaType.TXT,
        }
        return extension_map.get(ext, MediaType.UNKNOWN)

    def _is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube video or playlist."""
        return any(re.match(pattern, url) for pattern in self.YOUTUBE_PATTERNS)

    def _is_github_url(self, url: str) -> bool:
        """Check if URL is a GitHub repository."""
        return any(re.match(pattern, url) for pattern in self.GITHUB_PATTERNS)

    def _is_git_url(self, url: str) -> bool:
        """Check if URL is a git repository URL (SSH, git://, etc.)."""
        return any(re.match(pattern, url) for pattern in self.GIT_PATTERNS)

    def _is_pdf_url(self, url: str) -> bool:
        """Check if URL points to a PDF file."""
        if not self._is_web_url(url):
            return False
        # Check for .pdf extension (case insensitive)
        # Handle URLs with query strings: https://example.com/paper.pdf?download=true
        url_lower = url.lower()
        # Remove query string and fragment for extension check
        url_path = url_lower.split("?")[0].split("#")[0]
        return url_path.endswith(".pdf")

    def _is_web_url(self, url: str) -> bool:
        """Check if string is a web URL."""
        return bool(re.match(self.WEB_PATTERN, url))
