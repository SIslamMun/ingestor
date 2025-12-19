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

        if self._is_web_url(source_str):
            return MediaType.WEB

        # Check for .url files (contain URLs to crawl)
        if source_str.lower().endswith(".url"):
            return MediaType.WEB

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
        """Detect file type using Magika."""
        try:
            result = self.magika.identify_path(path)
            label = result.output.label.lower()
            return self.MAGIKA_TO_MEDIA_TYPE.get(label, MediaType.UNKNOWN)
        except Exception:
            # Fallback to extension if Magika fails
            return self._detect_by_extension(path)

    def _detect_by_extension(self, path: Path) -> MediaType:
        """Fallback detection by file extension."""
        ext = path.suffix.lower().lstrip(".")
        extension_map = {
            "pdf": MediaType.PDF,
            "docx": MediaType.DOCX,
            "doc": MediaType.DOCX,
            "pptx": MediaType.PPTX,
            "ppt": MediaType.PPTX,
            "xlsx": MediaType.XLSX,
            "xls": MediaType.XLS,
            "csv": MediaType.CSV,
            "epub": MediaType.EPUB,
            "mp3": MediaType.AUDIO,
            "wav": MediaType.AUDIO,
            "flac": MediaType.AUDIO,
            "m4a": MediaType.AUDIO,
            "json": MediaType.JSON,
            "xml": MediaType.XML,
            "zip": MediaType.ZIP,
            "tar": MediaType.ZIP,
            "gz": MediaType.ZIP,
            "png": MediaType.IMAGE,
            "jpg": MediaType.IMAGE,
            "jpeg": MediaType.IMAGE,
            "gif": MediaType.IMAGE,
            "webp": MediaType.IMAGE,
            "txt": MediaType.TXT,
            "md": MediaType.TXT,
            "rst": MediaType.TXT,
            "html": MediaType.TXT,
            "htm": MediaType.TXT,
        }
        return extension_map.get(ext, MediaType.UNKNOWN)

    def _is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube video or playlist."""
        return any(re.match(pattern, url) for pattern in self.YOUTUBE_PATTERNS)

    def _is_github_url(self, url: str) -> bool:
        """Check if URL is a GitHub repository."""
        return any(re.match(pattern, url) for pattern in self.GITHUB_PATTERNS)

    def _is_web_url(self, url: str) -> bool:
        """Check if string is a web URL."""
        return bool(re.match(self.WEB_PATTERN, url))
