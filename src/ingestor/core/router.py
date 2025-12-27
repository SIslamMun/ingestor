"""Router for directing inputs to the appropriate extractors."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from ..types import ExtractionResult, IngestConfig, MediaType
from .registry import ExtractorRegistry


class Router:
    """Route inputs to the appropriate extractors.

    The router handles:
    - Single file/URL processing
    - Batch directory processing
    - .url file processing (files containing URLs to crawl)
    """

    def __init__(self, registry: ExtractorRegistry, config: IngestConfig | None = None):
        """Initialize the router.

        Args:
            registry: Extractor registry to use
            config: Configuration for ingestion operations
        """
        self.registry = registry
        self.config = config or IngestConfig()

    async def process(self, source: str | Path) -> ExtractionResult:
        """Process a single source (file or URL).

        Args:
            source: File path or URL to process

        Returns:
            Extraction result

        Raises:
            ValueError: If no extractor is available for the source
        """
        extractor = self.registry.get_for_source(source)
        if extractor is None:
            media_type = self.registry.detector.detect(source)
            raise ValueError(
                f"No extractor available for {source} (detected type: {media_type.value})"
            )

        return await extractor.extract(source)

    async def process_batch(
        self, sources: list[str | Path], concurrency: int = 5
    ) -> AsyncIterator[ExtractionResult]:
        """Process multiple sources concurrently.

        Args:
            sources: List of file paths or URLs
            concurrency: Maximum number of concurrent extractions

        Yields:
            Extraction results as they complete
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def process_with_semaphore(source: str | Path) -> ExtractionResult:
            async with semaphore:
                return await self.process(source)

        tasks = [asyncio.create_task(process_with_semaphore(s)) for s in sources]

        for task in asyncio.as_completed(tasks):
            yield await task

    async def process_directory(
        self,
        directory: str | Path,
        recursive: bool = True,
        concurrency: int = 5,
    ) -> AsyncIterator[ExtractionResult]:
        """Process all supported files in a directory.

        Args:
            directory: Directory to process
            recursive: Whether to process subdirectories
            concurrency: Maximum number of concurrent extractions

        Yields:
            Extraction results as they complete
        """
        directory = Path(directory)
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        # Collect all files
        sources: list[str | Path] = []
        pattern = "**/*" if recursive else "*"

        for path in directory.glob(pattern):
            if path.is_file():
                # Check if we have an extractor for this file
                if self.registry.get_for_source(path) is not None:
                    sources.append(path)
                # Handle .url files specially
                elif path.suffix.lower() == ".url":
                    sources.extend(self._parse_url_file(path))
                # Handle .download_git files specially
                elif path.suffix.lower() == ".download_git":
                    sources.extend(self._parse_download_git_file(path))

        async for result in self.process_batch(sources, concurrency):
            yield result

    def _parse_url_file(self, path: Path) -> list[str]:
        """Parse a .url file containing URLs to crawl.

        Each line in the file should be a URL. Empty lines and lines
        starting with # are ignored.

        Args:
            path: Path to the .url file

        Returns:
            List of URLs from the file
        """
        urls: list[str] = []
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        urls.append(line)
        except Exception:
            pass
        return urls

    def _parse_download_git_file(self, path: Path) -> list[str]:
        """Parse a .download_git file containing git repository URLs.

        Each line in the file should be a git URL (HTTPS, SSH, or git://).
        Empty lines and lines starting with # are ignored.

        Args:
            path: Path to the .download_git file

        Returns:
            List of git URLs from the file
        """
        urls: list[str] = []
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        urls.append(line)
        except Exception:
            pass
        return urls

    def detect_type(self, source: str | Path) -> MediaType:
        """Detect the media type of a source.

        Args:
            source: File path or URL

        Returns:
            Detected media type
        """
        return self.registry.detector.detect(source)

    def can_process(self, source: str | Path) -> bool:
        """Check if a source can be processed.

        Args:
            source: File path or URL

        Returns:
            True if an extractor is available
        """
        return self.registry.get_for_source(source) is not None
