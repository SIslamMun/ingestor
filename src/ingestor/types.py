"""Core types for the ingestor package."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class MediaType(Enum):
    """Supported media types for ingestion."""

    # Documents
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    EPUB = "epub"

    # Spreadsheets
    XLSX = "xlsx"
    XLS = "xls"
    CSV = "csv"

    # Web
    WEB = "web"
    YOUTUBE = "youtube"
    GITHUB = "github"

    # Audio
    AUDIO = "audio"

    # Data formats
    JSON = "json"
    XML = "xml"

    # Archives
    ZIP = "zip"

    # Text
    TXT = "txt"

    # Images
    IMAGE = "image"

    # Unknown
    UNKNOWN = "unknown"


@dataclass
class ExtractedImage:
    """Represents an image extracted from a document."""

    filename: str
    data: bytes
    format: str  # png, jpg, gif, etc.
    page: Optional[int] = None  # Page/slide number where image was found
    caption: Optional[str] = None  # Extracted caption if available
    context: Optional[str] = None  # Surrounding text for context
    description: Optional[str] = None  # VLM-generated description (if --describe)

    @property
    def size_bytes(self) -> int:
        """Return the size of the image in bytes."""
        return len(self.data)


@dataclass
class ExtractionResult:
    """Result of extracting content from a source."""

    markdown: str
    title: Optional[str] = None
    source: Optional[str] = None  # Original file path or URL
    media_type: Optional[MediaType] = None
    images: list[ExtractedImage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    charset: Optional[str] = None  # Detected charset for text files

    @property
    def has_images(self) -> bool:
        """Check if the result contains any images."""
        return len(self.images) > 0

    @property
    def image_count(self) -> int:
        """Return the number of extracted images."""
        return len(self.images)


@dataclass
class IngestConfig:
    """Configuration for ingestion operations."""

    output_dir: Path = field(default_factory=lambda: Path("./output"))
    keep_raw_images: bool = False  # Keep original image formats
    target_image_format: str = "png"  # Convert images to this format
    generate_metadata: bool = False  # Generate metadata.json files
    verbose: bool = False

    # AI features (optional)
    describe_images: bool = False  # Use VLM for image descriptions
    use_agent: bool = False  # Use Claude agent for cleanup

    # Web crawl options
    crawl_strategy: str = "bfs"  # bfs, dfs, bestfirst
    crawl_max_depth: int = 2
    crawl_max_pages: int = 50

    # YouTube options
    youtube_captions: str = "auto"  # auto or manual
    youtube_playlist: bool = False

    # Audio options
    whisper_model: str = "turbo"

    # VLM options
    ollama_host: str = "http://localhost:11434"
    vlm_model: str = "llava:7b"
