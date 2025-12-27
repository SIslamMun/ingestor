"""Image naming conventions for consistent output."""

import re
from pathlib import Path

from ..types import ExtractedImage


class ImageNamer:
    """Generate consistent filenames for extracted images.

    Supports various naming patterns:
    - sequential: figure_001.png, figure_002.png
    - page_based: page1_img1.png, page2_img1.png
    - source_based: document_001.png, document_002.png
    """

    def __init__(
        self,
        pattern: str = "figure_{num:03d}",
        prefix: str | None = None,
    ):
        """Initialize image namer.

        Args:
            pattern: Naming pattern with {num}, {page}, {ext} placeholders
            prefix: Optional prefix for all filenames
        """
        self.pattern = pattern
        self.prefix = prefix
        self._counter = 0
        self._page_counters: dict[int, int] = {}

    def reset(self) -> None:
        """Reset counters."""
        self._counter = 0
        self._page_counters.clear()

    def generate(
        self,
        image: ExtractedImage,
        source_name: str | None = None,
    ) -> str:
        """Generate a filename for an image.

        Args:
            image: The extracted image
            source_name: Optional source document name

        Returns:
            Generated filename
        """
        self._counter += 1

        # Track per-page counter
        page = image.page or 0
        if page not in self._page_counters:
            self._page_counters[page] = 0
        self._page_counters[page] += 1

        # Build replacement dict
        replacements = {
            "num": self._counter,
            "page": page,
            "page_num": self._page_counters[page],
            "ext": image.format or "png",
            "source": self._sanitize(source_name) if source_name else "image",
        }

        # Apply pattern
        filename = self.pattern
        for key, value in replacements.items():
            # Handle format specifiers like {num:03d}
            pattern = rf"\{{{key}(?::[^}}]+)?\}}"
            match = re.search(pattern, filename)
            if match:
                format_spec = match.group(0)
                try:
                    formatted = format_spec.format(**{key: value})
                    filename = filename.replace(match.group(0), formatted)
                except (KeyError, ValueError):
                    filename = filename.replace(match.group(0), str(value))

        # Add extension if not present
        if not filename.endswith(f".{image.format}"):
            filename = f"{filename}.{image.format}"

        # Add prefix
        if self.prefix:
            filename = f"{self.prefix}_{filename}"

        return filename

    def rename(
        self,
        image: ExtractedImage,
        source_name: str | None = None,
    ) -> ExtractedImage:
        """Rename an image and return a new ExtractedImage.

        Args:
            image: The extracted image
            source_name: Optional source document name

        Returns:
            New ExtractedImage with updated filename
        """
        new_filename = self.generate(image, source_name)

        return ExtractedImage(
            filename=new_filename,
            data=image.data,
            format=image.format,
            page=image.page,
            caption=image.caption,
            context=image.context,
            description=image.description,
        )

    def rename_all(
        self,
        images: list[ExtractedImage],
        source_name: str | None = None,
    ) -> list[ExtractedImage]:
        """Rename all images with consistent naming.

        Args:
            images: List of extracted images
            source_name: Optional source document name

        Returns:
            List of renamed images
        """
        self.reset()
        return [self.rename(img, source_name) for img in images]

    def _sanitize(self, name: str) -> str:
        """Sanitize a name for use in filenames.

        Args:
            name: Name to sanitize

        Returns:
            Sanitized name
        """
        # Remove extension
        name = Path(name).stem

        # Replace spaces and special chars
        name = re.sub(r"[^\w\-]", "_", name)

        # Remove multiple underscores
        name = re.sub(r"_+", "_", name)

        # Trim underscores
        name = name.strip("_")

        # Limit length
        if len(name) > 50:
            name = name[:50]

        return name.lower()


# Common naming patterns
PATTERNS = {
    "sequential": "figure_{num:03d}",
    "page_based": "page{page}_img{page_num}",
    "source_based": "{source}_{num:03d}",
    "slide_based": "slide{page}_img{page_num}",
}


def create_namer(style: str = "sequential", prefix: str | None = None) -> ImageNamer:
    """Create an image namer with a predefined style.

    Args:
        style: Naming style (sequential, page_based, source_based, slide_based)
        prefix: Optional prefix

    Returns:
        Configured ImageNamer
    """
    pattern = PATTERNS.get(style, PATTERNS["sequential"])
    return ImageNamer(pattern=pattern, prefix=prefix)
