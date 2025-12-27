"""PowerPoint extractor using python-pptx."""

from pathlib import Path

from ...types import ExtractedImage, ExtractionResult, MediaType
from ..base import BaseExtractor


class PptxExtractor(BaseExtractor):
    """Extract content and images from PowerPoint presentations.

    Uses python-pptx for extraction with shape.image.blob for images.
    """

    media_type = MediaType.PPTX

    async def extract(self, source: str | Path) -> ExtractionResult:
        """Extract content from a PPTX file.

        Args:
            source: Path to the PPTX file

        Returns:
            Extraction result with markdown and images
        """
        from pptx import Presentation
        from pptx.enum.shapes import MSO_SHAPE_TYPE

        path = Path(source)
        prs = Presentation(str(path))

        slides_md = []
        images: list[ExtractedImage] = []
        img_counter = 0

        for slide_num, slide in enumerate(prs.slides, 1):
            slide_lines = [f"## Slide {slide_num}"]

            # Extract title if present
            if slide.shapes.title and slide.shapes.title.text:
                slide_lines.append(f"### {slide.shapes.title.text.strip()}")
                slide_lines.append("")

            # Extract content from shapes
            for shape in slide.shapes:
                # Extract text
                if hasattr(shape, "text_frame"):
                    for para in shape.text_frame.paragraphs:
                        text = para.text.strip()
                        if text:
                            # Check if it's a bullet point
                            if para.level > 0:
                                indent = "  " * para.level
                                slide_lines.append(f"{indent}- {text}")
                            else:
                                slide_lines.append(text)

                # Extract images (always)
                if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    try:
                        image = shape.image
                        img_counter += 1
                        ext = image.ext.lower()
                        if ext == "jpg":
                            ext = "jpeg"

                        images.append(ExtractedImage(
                            filename=f"slide{slide_num}_img{img_counter}.{image.ext}",
                            data=image.blob,
                            format=ext,
                            page=slide_num,
                        ))

                        # Add image reference in markdown
                        slide_lines.append(f"![Image {img_counter}](./img/slide{slide_num}_img{img_counter}.{image.ext})")
                    except Exception:
                        pass  # Skip images that can't be extracted

                # Extract tables
                if shape.has_table:
                    table_md = self._extract_table(shape.table)
                    slide_lines.append(table_md)

            slides_md.append("\n".join(slide_lines))

        markdown = "\n\n---\n\n".join(slides_md)

        # Get title from first slide
        title = None
        if prs.slides and prs.slides[0].shapes.title:
            title = prs.slides[0].shapes.title.text

        return ExtractionResult(
            markdown=markdown,
            title=title or path.stem,
            source=str(path),
            media_type=MediaType.PPTX,
            images=images,
            metadata={
                "slide_count": len(prs.slides),
                "image_count": len(images),
            },
        )

    def _extract_table(self, table) -> str:
        """Extract a table as markdown.

        Args:
            table: pptx Table object

        Returns:
            Markdown table string
        """
        rows = []
        for row in table.rows:
            cells = []
            for cell in row.cells:
                text = cell.text.strip().replace("|", "\\|")
                cells.append(text)
            rows.append("| " + " | ".join(cells) + " |")

        if not rows:
            return ""

        # Add header separator after first row
        header_sep = "| " + " | ".join(["---"] * len(table.columns)) + " |"
        rows.insert(1, header_sep)

        return "\n".join(rows)

    def supports(self, source: str | Path) -> bool:
        """Check if this extractor handles the source.

        Args:
            source: Path to check

        Returns:
            True if this is a PPTX file
        """
        return str(source).lower().endswith((".pptx", ".ppt"))
