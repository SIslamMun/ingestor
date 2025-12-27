"""Core infrastructure for the ingestor package."""

from .charset import CharsetHandler
from .detector import FileDetector
from .registry import ExtractorRegistry, create_default_registry
from .router import Router

__all__ = [
    "FileDetector",
    "CharsetHandler",
    "ExtractorRegistry",
    "create_default_registry",
    "Router",
]
