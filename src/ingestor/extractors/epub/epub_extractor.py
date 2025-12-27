"""EPUB ebook extractor using ebooklib."""

import re
from pathlib import Path

from markdownify import markdownify

from ...types import ExtractedImage, ExtractionResult, MediaType
from ..base import BaseExtractor


class EpubExtractor(BaseExtractor):
    """Extract content and images from EPUB ebooks.

    Uses ebooklib for EPUB2/EPUB3 support.
    Images are extracted and paths in markdown are rewritten to ./img/filename.
    """

    media_type = MediaType.EPUB

    async def extract(self, source: str | Path) -> ExtractionResult:
        """Extract content from an EPUB file.

        Args:
            source: Path to the EPUB file

        Returns:
            Extraction result with markdown and images
        """
        from ebooklib import ITEM_DOCUMENT, ITEM_IMAGE, epub

        path = Path(source)
        book = epub.read_epub(str(path))

        chapters = []
        images: list[ExtractedImage] = []

        # Build image path mapping: original_path -> new_filename
        image_map: dict[str, str] = {}

        # Extract metadata
        title = None
        title_meta = book.get_metadata("DC", "title")
        if title_meta:
            title = title_meta[0][0]

        author = None
        author_meta = book.get_metadata("DC", "creator")
        if author_meta:
            author = author_meta[0][0]

        # Extract images first and build path mapping
        for item in book.get_items_of_type(ITEM_IMAGE):
            try:
                original_path = item.get_name()  # e.g., "OEBPS/images/fig1.png" or "images/fig1.png"
                filename = original_path.split("/")[-1]  # Get just the filename
                media_type_str = item.media_type  # e.g., "image/jpeg"
                ext = media_type_str.split("/")[-1] if "/" in media_type_str else "png"
                if ext == "jpg":
                    ext = "jpeg"

                # Create unique filename if needed
                if filename in [img.filename for img in images]:
                    base, extension = filename.rsplit(".", 1) if "." in filename else (filename, ext)
                    filename = f"{base}_{len(images)+1}.{extension}"

                images.append(ExtractedImage(
                    filename=filename,
                    data=item.get_content(),
                    format=ext,
                ))

                # Map all possible path variations to new filename
                # EPUB image refs can be relative: ../images/fig.png, images/fig.png, fig.png
                image_map[original_path] = filename
                image_map[original_path.split("/")[-1]] = filename  # Just filename
                # Handle relative paths from chapter directories
                for i in range(len(original_path.split("/"))):
                    partial = "/".join(original_path.split("/")[i:])
                    image_map[partial] = filename
                    image_map["../" + partial] = filename

            except Exception:
                pass

        # Extract chapters/documents
        for item in book.get_items_of_type(ITEM_DOCUMENT):
            try:
                content = item.get_content().decode("utf-8")
                # Convert HTML to markdown
                md = markdownify(content, heading_style="ATX", strip=["script", "style"])
                md = self._clean_markdown(md)

                # Rewrite image paths to point to ./img/
                md = self._rewrite_image_paths(md, image_map)

                if md.strip():
                    chapters.append(md)
            except Exception:
                pass

        # Build markdown with chapter separators
        markdown_parts = []
        if title:
            markdown_parts.append(f"# {title}")
            if author:
                markdown_parts.append(f"\n**Author:** {author}\n")
            markdown_parts.append("")

        markdown_parts.append("\n\n---\n\n".join(chapters))

        return ExtractionResult(
            markdown="\n".join(markdown_parts),
            title=title or path.stem,
            source=str(path),
            media_type=MediaType.EPUB,
            images=images,
            metadata={
                "author": author,
                "chapter_count": len(chapters),
                "image_count": len(images),
            },
        )

    def _rewrite_image_paths(self, markdown: str, image_map: dict[str, str]) -> str:
        """Rewrite image paths in markdown to point to ./img/.

        Args:
            markdown: Markdown content with original image refs
            image_map: Mapping of original paths to new filenames

        Returns:
            Markdown with rewritten image paths
        """
        # Pattern to match markdown images: ![alt](path)
        img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')

        def replace_path(match):
            alt_text = match.group(1)
            original_path = match.group(2)

            # Try to find the image in our map
            # Clean up the path (remove URL encoding, etc.)
            clean_path = original_path.replace("%20", " ")

            # Try various path forms
            new_filename = None
            for path_variant in [clean_path, clean_path.split("/")[-1], original_path]:
                if path_variant in image_map:
                    new_filename = image_map[path_variant]
                    break

            if new_filename:
                return f"![{alt_text}](./img/{new_filename})"
            else:
                # Keep original if we can't find it
                return match.group(0)

        return img_pattern.sub(replace_path, markdown)

    def _clean_markdown(self, markdown: str) -> str:
        """Clean up markdown output.

        Args:
            markdown: Raw markdown

        Returns:
            Cleaned markdown
        """
        lines = []
        prev_blank = False

        for line in markdown.split("\n"):
            is_blank = not line.strip()
            if is_blank:
                if not prev_blank:
                    lines.append("")
                prev_blank = True
            else:
                lines.append(line.rstrip())
                prev_blank = False

        return "\n".join(lines).strip()

    def supports(self, source: str | Path) -> bool:
        """Check if this extractor handles the source.

        Args:
            source: Path to check

        Returns:
            True if this is an EPUB file
        """
        return str(source).lower().endswith(".epub")
