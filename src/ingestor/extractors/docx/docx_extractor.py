"""Word document extractor using mammoth with inline image support."""

import hashlib
from pathlib import Path
from typing import List, Union

from markdownify import markdownify

from ...types import ExtractionResult, ExtractedImage, MediaType
from ..base import BaseExtractor


class DocxExtractor(BaseExtractor):
    """Extract content and images from Word documents.

    Uses mammoth with custom image handler to preserve image positions
    in the output markdown. Images are extracted inline with
    ![](./img/filename.ext) references at their original positions.
    """

    media_type = MediaType.DOCX

    async def extract(self, source: Union[str, Path]) -> ExtractionResult:
        """Extract content from a DOCX file.

        Args:
            source: Path to the DOCX file

        Returns:
            Extraction result with markdown and images
        """
        import mammoth

        path = Path(source)
        images: List[ExtractedImage] = []
        img_counter = [0]  # Use list for closure mutability

        def convert_image(image):
            """Custom image converter that extracts and references images inline."""
            img_counter[0] += 1
            
            with image.open() as img_file:
                img_data = img_file.read()
            
            # Determine extension from content type
            content_type = image.content_type or "image/png"
            ext = content_type.split("/")[-1].lower()
            if ext == "jpg":
                ext = "jpeg"
            elif ext not in ("png", "jpeg", "gif", "webp", "svg"):
                ext = "png"
            
            # Generate unique filename using hash
            img_hash = hashlib.md5(img_data).hexdigest()[:8]
            filename = f"image_{img_counter[0]}_{img_hash}.{ext}"
            
            # Store image for extraction
            images.append(ExtractedImage(
                filename=filename,
                data=img_data,
                format=ext,
            ))
            
            # Return image element with path to extracted image
            return {"src": f"./img/{filename}"}

        # Use mammoth with custom image handler
        with open(path, "rb") as f:
            result = mammoth.convert_to_html(
                f,
                convert_image=mammoth.images.img_element(convert_image)
            )
            html = result.value

        # Convert HTML to Markdown (preserves img tags as ![](src))
        markdown = markdownify(html, heading_style="ATX", strip=["script", "style"])

        # Clean up markdown
        markdown = self._clean_markdown(markdown)

        # Get title from first heading or filename
        title = self._extract_title(markdown) or path.stem

        return ExtractionResult(
            markdown=markdown,
            title=title,
            source=str(path),
            media_type=MediaType.DOCX,
            images=images,
            metadata={
                "image_count": len(images),
                "warnings": result.messages if result.messages else [],
            },
        )

    def _extract_title(self, markdown: str) -> str:
        """Extract title from first heading.

        Args:
            markdown: Markdown content

        Returns:
            Title or empty string
        """
        for line in markdown.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return ""

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
            # Remove excessive blank lines
            is_blank = not line.strip()
            if is_blank:
                if not prev_blank:
                    lines.append("")
                prev_blank = True
            else:
                lines.append(line.rstrip())
                prev_blank = False

        return "\n".join(lines).strip()

    def supports(self, source: Union[str, Path]) -> bool:
        """Check if this extractor handles the source.

        Args:
            source: Path to check

        Returns:
            True if this is a DOCX file
        """
        return str(source).lower().endswith((".docx", ".doc"))
