"""Base extractor class that all format extractors inherit from."""

from abc import ABC, abstractmethod
from pathlib import Path

from ..types import ExtractionResult, MediaType


class BaseExtractor(ABC):
    """Abstract base class for all media extractors.

    All extractors must implement:
    - extract(): Extract content from a source
    - supports(): Check if this extractor handles the given source
    """

    media_type: MediaType

    @abstractmethod
    async def extract(self, source: str | Path) -> ExtractionResult:
        """Extract content and images from the source.

        Args:
            source: File path or URL to extract from

        Returns:
            ExtractionResult containing markdown, images, and metadata
        """
        pass

    @abstractmethod
    def supports(self, source: str | Path) -> bool:
        """Check if this extractor can handle the given source.

        Args:
            source: File path or URL to check

        Returns:
            True if this extractor can handle the source
        """
        pass

    @classmethod
    def get_name(cls) -> str:
        """Get the name of this extractor."""
        return cls.__name__.replace("Extractor", "").lower()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} media_type={self.media_type.value}>"
