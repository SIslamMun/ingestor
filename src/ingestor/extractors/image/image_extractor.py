"""Image extractor with EXIF metadata extraction."""

from pathlib import Path
from typing import Any

from ...types import ExtractedImage, ExtractionResult, MediaType
from ..base import BaseExtractor


class ImageExtractor(BaseExtractor):
    """Extract metadata and content from image files.

    Extracts:
    - EXIF metadata (camera, settings, GPS, etc.)
    - Image dimensions and format
    - The image itself for further processing
    """

    media_type = MediaType.IMAGE

    # Supported image extensions
    IMAGE_EXTENSIONS = {
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif",
        ".webp", ".ico", ".svg", ".heic", ".heif",
    }

    async def extract(self, source: str | Path) -> ExtractionResult:
        """Extract metadata from an image file.

        Args:
            source: Path to the image file

        Returns:
            Extraction result with metadata and image
        """
        path = Path(source)

        # Check if it's an SVG file (by content, not just extension)
        try:
            content = path.read_bytes()
            if content.strip().startswith(b'<?xml') or content.strip().startswith(b'<svg'):
                return self._extract_svg(path, content)
        except Exception:
            pass

        # Handle raster images with PIL
        return await self._extract_raster_image(path)

    async def _extract_raster_image(self, path: Path) -> ExtractionResult:
        """Extract metadata from a raster image file (PNG, JPG, etc.)."""
        from PIL import Image

        # Read image
        with Image.open(path) as img:
            # Basic info
            width, height = img.size
            format_name = img.format or path.suffix[1:].upper()
            mode = img.mode

            # Extract EXIF
            exif_data = self._extract_exif(img)

            # Read raw bytes for the extracted image
            img_bytes = path.read_bytes()

        # Determine format
        ext = path.suffix[1:].lower()
        if ext == "jpg":
            ext = "jpeg"

        # Create extracted image
        images = [
            ExtractedImage(
                filename=path.name,
                data=img_bytes,
                format=ext,
            )
        ]

        # Build markdown
        markdown = self._build_markdown(path, width, height, format_name, mode, exif_data)

        return ExtractionResult(
            markdown=markdown,
            title=path.stem,
            source=str(path),
            media_type=MediaType.IMAGE,
            images=images,
            metadata={
                "width": width,
                "height": height,
                "format": format_name,
                "mode": mode,
                **exif_data,
            },
        )

    def _extract_svg(self, path: Path, content: bytes) -> ExtractionResult:
        """Extract metadata from an SVG file."""
        import re

        # Try to decode the content
        try:
            svg_text = content.decode('utf-8')
        except UnicodeDecodeError:
            svg_text = content.decode('latin-1')

        # Try to extract dimensions from SVG
        width = height = "unknown"

        # Look for width/height attributes
        width_match = re.search(r'width=["\']?(\d+(?:\.\d+)?)', svg_text)
        height_match = re.search(r'height=["\']?(\d+(?:\.\d+)?)', svg_text)

        if width_match:
            width = width_match.group(1)
        if height_match:
            height = height_match.group(1)

        # Look for viewBox
        viewbox_match = re.search(r'viewBox=["\']?[\d.\s]+\s+([\d.]+)\s+([\d.]+)', svg_text)
        if viewbox_match and width == "unknown":
            width = viewbox_match.group(1)
            height = viewbox_match.group(2)

        # Build markdown
        markdown = f"""# Image: {path.name}

| Property | Value |
|----------|-------|
| **File** | {path.name} |
| **Format** | SVG (Scalable Vector Graphics) |
| **Width** | {width} |
| **Height** | {height} |
| **Size** | {len(content):,} bytes |

> **Note:** SVG is a vector image format stored as XML text.
"""

        # Create extracted image
        images = [
            ExtractedImage(
                filename=path.name,
                data=content,
                format="svg",
            )
        ]

        return ExtractionResult(
            markdown=markdown,
            title=path.stem,
            source=str(path),
            media_type=MediaType.IMAGE,
            images=images,
            metadata={
                "width": width,
                "height": height,
                "format": "SVG",
                "size_bytes": len(content),
            },
        )

    def _extract_exif(self, img) -> dict:
        """Extract EXIF metadata from image.

        Args:
            img: PIL Image object

        Returns:
            Dictionary of EXIF data
        """
        from PIL.ExifTags import GPSTAGS, TAGS

        exif_data: dict[str, Any] = {}

        try:
            exif = img._getexif()
            if not exif:
                return exif_data

            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)

                # Skip binary data
                if isinstance(value, bytes):
                    continue

                # Handle GPS info specially
                if tag == "GPSInfo":
                    gps_data = {}
                    for gps_tag_id, gps_value in value.items():
                        gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                        if not isinstance(gps_value, bytes):
                            gps_data[gps_tag] = self._convert_value(gps_value)
                    if gps_data:
                        exif_data["GPS"] = gps_data
                else:
                    exif_data[tag] = self._convert_value(value)

        except Exception:
            pass

        return exif_data

    def _convert_value(self, value):
        """Convert EXIF value to serializable format.

        Args:
            value: EXIF value

        Returns:
            Serializable value
        """
        if isinstance(value, tuple):
            return [self._convert_value(v) for v in value]
        if isinstance(value, bytes):
            return None
        if hasattr(value, "numerator"):
            # IFDRational
            if value.denominator:
                return float(value.numerator) / float(value.denominator)
            return float(value.numerator)
        return value

    def _build_markdown(
        self,
        path: Path,
        width: int,
        height: int,
        format_name: str,
        mode: str,
        exif_data: dict,
    ) -> str:
        """Build markdown from image metadata.

        Args:
            path: Image file path
            width: Image width
            height: Image height
            format_name: Image format
            mode: Color mode
            exif_data: EXIF metadata

        Returns:
            Markdown content
        """
        lines = [
            f"# Image: {path.name}",
            "",
            f"![{path.stem}](./img/{path.name})",
            "",
            "## Properties",
            "",
            "| Property | Value |",
            "| --- | --- |",
            f"| Dimensions | {width} × {height} |",
            f"| Format | {format_name} |",
            f"| Color Mode | {mode} |",
        ]

        # Add EXIF data
        if exif_data:
            lines.append("")
            lines.append("## EXIF Metadata")
            lines.append("")
            lines.append("| Tag | Value |")
            lines.append("| --- | --- |")

            # Priority fields
            priority_fields = ["Make", "Model", "DateTime", "ExposureTime", "FNumber", "ISO"]
            for field in priority_fields:
                if field in exif_data:
                    value = exif_data[field]
                    if isinstance(value, list):
                        value = ", ".join(str(v) for v in value)
                    lines.append(f"| {field} | {value} |")

            # Other fields
            for key, value in exif_data.items():
                if key not in priority_fields and key != "GPS":
                    if isinstance(value, list):
                        value = ", ".join(str(v) for v in value)
                    # Truncate long values
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:97] + "..."
                    lines.append(f"| {key} | {value_str} |")

            # GPS data
            if "GPS" in exif_data:
                lines.append("")
                lines.append("## GPS Data")
                lines.append("")
                lines.append("| Tag | Value |")
                lines.append("| --- | --- |")
                for key, value in exif_data["GPS"].items():
                    if isinstance(value, list):
                        value = ", ".join(str(v) for v in value)
                    lines.append(f"| {key} | {value} |")

        return "\n".join(lines)

    def supports(self, source: str | Path) -> bool:
        """Check if this extractor handles the source.

        Args:
            source: Path to check

        Returns:
            True if this is an image file
        """
        suffix = Path(source).suffix.lower()
        return suffix in self.IMAGE_EXTENSIONS
