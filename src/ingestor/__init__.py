"""Ingestor - Comprehensive media-to-markdown ingestion for LLM RAG and fine-tuning."""

__version__ = "0.1.0"

from .core import (
    CharsetHandler,
    ExtractorRegistry,
    FileDetector,
    Router,
    create_default_registry,
)
from .types import ExtractedImage, ExtractionResult, IngestConfig, MediaType

__all__ = [
    # Version
    "__version__",
    # Types
    "MediaType",
    "ExtractedImage",
    "ExtractionResult",
    "IngestConfig",
    # Core
    "FileDetector",
    "CharsetHandler",
    "ExtractorRegistry",
    "create_default_registry",
    "Router",
]
