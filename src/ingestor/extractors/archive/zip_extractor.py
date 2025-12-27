"""ZIP archive extractor with recursive content processing."""

import tempfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from ...types import ExtractedImage, ExtractionResult, MediaType
from ..base import BaseExtractor

if TYPE_CHECKING:
    from ...core.registry import ExtractorRegistry


class ZipExtractor(BaseExtractor):
    """Extract and process contents from ZIP archives.

    Recursively processes all files in the archive using appropriate
    extractors for each file type.
    """

    media_type = MediaType.ZIP

    def __init__(self, registry: Optional["ExtractorRegistry"] = None):
        """Initialize ZIP extractor.

        Args:
            registry: Extractor registry for processing contents
        """
        self._registry = registry

    def set_registry(self, registry: "ExtractorRegistry"):
        """Set the extractor registry.

        Args:
            registry: Extractor registry to use
        """
        self._registry = registry

    async def extract(self, source: str | Path) -> ExtractionResult:
        """Extract content from a ZIP file.

        Args:
            source: Path to the ZIP file

        Returns:
            Extraction result with combined markdown from all files
        """
        path = Path(source)

        if not zipfile.is_zipfile(path):
            return ExtractionResult(
                markdown=f"# Error\n\nNot a valid ZIP file: {path.name}",
                title="Error",
                source=str(path),
                media_type=MediaType.ZIP,
                images=[],
                metadata={"error": "Invalid ZIP file"},
            )

        results = []
        all_images: list[ExtractedImage] = []
        file_count = 0
        processed_count = 0

        with zipfile.ZipFile(path, "r") as zf:
            # Get list of files
            file_list = [name for name in zf.namelist() if not name.endswith("/")]
            file_count = len(file_list)

            with tempfile.TemporaryDirectory() as tmpdir:
                # Extract all files
                zf.extractall(tmpdir)
                tmpdir_path = Path(tmpdir)

                # Process each file
                for file_name in file_list:
                    file_path = tmpdir_path / file_name

                    if not file_path.exists() or not file_path.is_file():
                        continue

                    # Try to extract with registry
                    if self._registry:
                        extractor = self._registry.get_for_source(file_path)
                        if extractor:
                            try:
                                result = await extractor.extract(file_path)
                                if result.markdown.strip():
                                    results.append({
                                        "name": file_name,
                                        "markdown": result.markdown,
                                    })
                                    # Prefix image filenames with archive path
                                    for img in result.images:
                                        img.filename = f"{Path(file_name).stem}_{img.filename}"
                                        all_images.append(img)
                                    processed_count += 1
                            except Exception:
                                pass

        # Build combined markdown
        markdown = self._build_markdown(path, results, file_count, processed_count)

        return ExtractionResult(
            markdown=markdown,
            title=path.stem,
            source=str(path),
            media_type=MediaType.ZIP,
            images=all_images,
            metadata={
                "file_count": file_count,
                "processed_count": processed_count,
                "image_count": len(all_images),
            },
        )

    def _build_markdown(
        self,
        path: Path,
        results: list[dict],
        file_count: int,
        processed_count: int,
    ) -> str:
        """Build combined markdown from extracted files.

        Args:
            path: Source archive path
            results: List of extraction results with name and markdown
            file_count: Total files in archive
            processed_count: Number of files successfully processed

        Returns:
            Combined markdown content
        """
        lines = [
            f"# Archive: {path.name}",
            "",
            f"**Total Files:** {file_count}",
            f"**Processed:** {processed_count}",
            "",
        ]

        if not results:
            lines.append("*No extractable content found in archive.*")
        else:
            lines.append("---")
            lines.append("")

            for result in results:
                lines.append(f"## {result['name']}")
                lines.append("")
                lines.append(result["markdown"])
                lines.append("")
                lines.append("---")
                lines.append("")

        return "\n".join(lines)

    def supports(self, source: str | Path) -> bool:
        """Check if this extractor handles the source.

        Args:
            source: Path to check

        Returns:
            True if this is a ZIP file
        """
        return str(source).lower().endswith(".zip")
