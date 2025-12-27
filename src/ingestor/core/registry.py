"""Extractor registry for managing available extractors."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..types import MediaType
from .detector import FileDetector

if TYPE_CHECKING:
    from ..extractors.base import BaseExtractor


class ExtractorRegistry:
    """Registry for managing and accessing extractors.

    The registry maintains a mapping of MediaType to Extractor instances
    and handles extractor lookup based on file type detection.
    """

    def __init__(self):
        """Initialize the registry."""
        self._extractors: dict[MediaType, BaseExtractor] = {}
        self._detector = FileDetector()

    def register(self, extractor: BaseExtractor) -> None:
        """Register an extractor for its media type.

        Args:
            extractor: Extractor instance to register
        """
        self._extractors[extractor.media_type] = extractor

    def register_class(
        self, extractor_class: type[BaseExtractor], *args, **kwargs
    ) -> None:
        """Register an extractor class (instantiates it).

        Args:
            extractor_class: Extractor class to instantiate and register
            *args: Arguments to pass to the constructor
            **kwargs: Keyword arguments to pass to the constructor
        """
        extractor = extractor_class(*args, **kwargs)
        self.register(extractor)

    def get(self, media_type: MediaType) -> BaseExtractor | None:
        """Get an extractor by media type.

        Args:
            media_type: The media type to get an extractor for

        Returns:
            Extractor instance or None if not registered
        """
        return self._extractors.get(media_type)

    def get_for_source(self, source: str | Path) -> BaseExtractor | None:
        """Get an extractor for a given source.

        Detects the media type using Magika and returns the appropriate extractor.

        Args:
            source: File path or URL

        Returns:
            Extractor instance or None if no suitable extractor
        """
        media_type = self._detector.detect(source)
        return self.get(media_type)

    def has(self, media_type: MediaType) -> bool:
        """Check if an extractor is registered for a media type.

        Args:
            media_type: The media type to check

        Returns:
            True if an extractor is registered
        """
        return media_type in self._extractors

    def list_supported(self) -> list[MediaType]:
        """List all supported media types.

        Returns:
            List of registered MediaType values
        """
        return list(self._extractors.keys())

    def list_extractors(self) -> list[BaseExtractor]:
        """List all registered extractors.

        Returns:
            List of registered extractor instances
        """
        return list(self._extractors.values())

    @property
    def detector(self) -> FileDetector:
        """Get the file detector instance."""
        return self._detector

    def __len__(self) -> int:
        """Return the number of registered extractors."""
        return len(self._extractors)

    def __contains__(self, media_type: MediaType) -> bool:
        """Check if a media type is registered."""
        return media_type in self._extractors


def create_default_registry() -> ExtractorRegistry:
    """Create a registry with all available extractors.

    Attempts to register each extractor, skipping those whose
    dependencies are not installed.

    Returns:
        Configured ExtractorRegistry
    """
    registry = ExtractorRegistry()

    # Text extractor (always available)
    try:
        from ..extractors.text import TxtExtractor
        registry.register(TxtExtractor())
    except ImportError:
        pass

    # PDF extractor (placeholder)
    try:
        from ..extractors.pdf import PdfExtractor
        registry.register(PdfExtractor())
    except ImportError:
        pass

    # Document extractors
    try:
        from ..extractors.docx import DocxExtractor
        registry.register(DocxExtractor())
    except ImportError:
        pass

    try:
        from ..extractors.pptx import PptxExtractor
        registry.register(PptxExtractor())
    except ImportError:
        pass

    try:
        from ..extractors.epub import EpubExtractor
        registry.register(EpubExtractor())
    except ImportError:
        pass

    # Spreadsheet extractors
    try:
        from ..extractors.excel import XlsxExtractor
        registry.register(XlsxExtractor())
    except ImportError:
        pass

    try:
        from ..extractors.excel import XlsExtractor
        registry.register(XlsExtractor())
    except ImportError:
        pass

    # Data extractors
    try:
        from ..extractors.data import CsvExtractor
        registry.register(CsvExtractor())
    except ImportError:
        pass

    try:
        from ..extractors.data import JsonExtractor
        registry.register(JsonExtractor())
    except ImportError:
        pass

    try:
        from ..extractors.data import XmlExtractor
        registry.register(XmlExtractor())
    except ImportError:
        pass

    # Web extractors
    try:
        from ..extractors.web import WebExtractor
        registry.register(WebExtractor())
    except ImportError:
        pass

    try:
        from ..extractors.youtube import YouTubeExtractor
        registry.register(YouTubeExtractor())
    except ImportError:
        pass

    # Audio extractor
    try:
        from ..extractors.audio import AudioExtractor
        registry.register(AudioExtractor())
    except ImportError:
        pass

    # Archive extractor (needs registry reference)
    try:
        from ..extractors.archive import ZipExtractor
        zip_extractor = ZipExtractor(registry=registry)
        registry.register(zip_extractor)
    except ImportError:
        pass

    # Image extractor
    try:
        from ..extractors.image import ImageExtractor
        registry.register(ImageExtractor())
    except ImportError:
        pass

    return registry
