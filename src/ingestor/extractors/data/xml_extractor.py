"""XML extractor using defusedxml for secure parsing."""

from pathlib import Path

from ...types import ExtractionResult, MediaType
from ..base import BaseExtractor


class XmlExtractor(BaseExtractor):
    """Extract content from XML files.

    Uses defusedxml for secure parsing (prevents XXE attacks).
    Converts XML structure to readable markdown.
    """

    media_type = MediaType.XML

    async def extract(self, source: str | Path) -> ExtractionResult:
        """Extract content from an XML file.

        Args:
            source: Path to the XML file

        Returns:
            Extraction result with markdown representation
        """
        import defusedxml.ElementTree as ET

        path = Path(source)

        tree = ET.parse(path)
        root = tree.getroot()

        # Generate markdown representation
        markdown = self._xml_to_markdown(root, path.stem)

        # Collect metadata
        metadata = {
            "root_tag": self._strip_namespace(root.tag),
            "element_count": self._count_elements(root),
        }

        return ExtractionResult(
            markdown=markdown,
            title=path.stem,
            source=str(path),
            media_type=MediaType.XML,
            images=[],
            metadata=metadata,
        )

    def _xml_to_markdown(self, root, title: str) -> str:
        """Convert XML element to markdown.

        Args:
            root: Root XML element
            title: Document title

        Returns:
            Markdown representation
        """
        lines = [f"# {title}", ""]

        root_tag = self._strip_namespace(root.tag)
        lines.append(f"**Root Element:** `{root_tag}`")
        lines.append("")

        # Show structure as code block
        lines.append("## Content")
        lines.append("")
        lines.append("```xml")
        lines.append(self._element_to_string(root, indent=0))
        lines.append("```")

        return "\n".join(lines)

    def _element_to_string(self, element, indent: int = 0) -> str:
        """Convert element to indented string representation.

        Args:
            element: XML element
            indent: Current indentation level

        Returns:
            String representation
        """
        lines = []
        prefix = "  " * indent
        tag = self._strip_namespace(element.tag)

        # Build opening tag with attributes
        attrs = " ".join(f'{k}="{v}"' for k, v in element.attrib.items())
        opening = f"<{tag} {attrs}>" if attrs else f"<{tag}>"

        # Check if element has children
        children = list(element)
        text = (element.text or "").strip()

        if not children and not text:
            # Self-closing tag
            if attrs:
                lines.append(f"{prefix}<{tag} {attrs}/>")
            else:
                lines.append(f"{prefix}<{tag}/>")
        elif not children:
            # Element with only text content
            lines.append(f"{prefix}{opening}{text}</{tag}>")
        else:
            # Element with children
            lines.append(f"{prefix}{opening}")
            if text:
                lines.append(f"{prefix}  {text}")
            for child in children:
                lines.append(self._element_to_string(child, indent + 1))
            lines.append(f"{prefix}</{tag}>")

        return "\n".join(lines)

    def _strip_namespace(self, tag: str) -> str:
        """Remove namespace prefix from tag.

        Args:
            tag: Tag with possible namespace

        Returns:
            Tag without namespace
        """
        if "}" in tag:
            return tag.split("}")[1]
        return tag

    def _count_elements(self, element) -> int:
        """Count total elements in tree.

        Args:
            element: Root element

        Returns:
            Total element count
        """
        count = 1
        for child in element:
            count += self._count_elements(child)
        return count

    def supports(self, source: str | Path) -> bool:
        """Check if this extractor handles the source.

        Args:
            source: Path to check

        Returns:
            True if this is an XML file
        """
        return str(source).lower().endswith(".xml")
