"""Markdown conversion utilities using markdownify."""

import re


class MarkdownConverter:
    """Convert HTML to clean Markdown.

    Uses markdownify with configurable options for
    heading style, link handling, and content cleanup.
    """

    def __init__(
        self,
        heading_style: str = "ATX",
        strip_tags: list[str] | None = None,
        autolinks: bool = True,
        escape_asterisks: bool = True,
        escape_underscores: bool = True,
    ):
        """Initialize converter.

        Args:
            heading_style: Heading style (ATX, ATX_CLOSED, SETEXT, UNDERLINED)
            strip_tags: HTML tags to remove entirely
            autolinks: Convert URLs to markdown links
            escape_asterisks: Escape asterisks in text
            escape_underscores: Escape underscores in text
        """
        self.heading_style = heading_style
        self.strip_tags = strip_tags or ["script", "style", "nav", "footer"]
        self.autolinks = autolinks
        self.escape_asterisks = escape_asterisks
        self.escape_underscores = escape_underscores

    def convert(self, html: str) -> str:
        """Convert HTML to Markdown.

        Args:
            html: HTML content

        Returns:
            Markdown content
        """
        from markdownify import markdownify

        markdown = markdownify(
            html,
            heading_style=self.heading_style,
            strip=self.strip_tags,
            autolinks=self.autolinks,
            escape_asterisks=self.escape_asterisks,
            escape_underscores=self.escape_underscores,
        )

        return self.clean(markdown)

    def clean(self, markdown: str) -> str:
        """Clean up markdown output.

        Args:
            markdown: Raw markdown

        Returns:
            Cleaned markdown
        """
        # Remove excessive blank lines
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)

        # Remove trailing whitespace from lines
        lines = [line.rstrip() for line in markdown.split("\n")]

        # Remove leading/trailing blank lines
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()

        return "\n".join(lines)

    def convert_with_images(
        self,
        html: str,
        image_base_path: str = "./img",
    ) -> str:
        """Convert HTML and fix image paths.

        Args:
            html: HTML content
            image_base_path: Base path for images

        Returns:
            Markdown with fixed image paths
        """
        markdown = self.convert(html)

        # Fix relative image paths
        markdown = re.sub(
            r"!\[([^\]]*)\]\((?!http)([^)]+)\)",
            rf"![\1]({image_base_path}/\2)",
            markdown,
        )

        return markdown


def html_to_markdown(
    html: str,
    heading_style: str = "ATX",
    strip_tags: list[str] | None = None,
) -> str:
    """Convert HTML to Markdown.

    Convenience function for one-off conversions.

    Args:
        html: HTML content
        heading_style: Heading style
        strip_tags: Tags to strip

    Returns:
        Markdown content
    """
    converter = MarkdownConverter(
        heading_style=heading_style,
        strip_tags=strip_tags,
    )
    return converter.convert(html)
