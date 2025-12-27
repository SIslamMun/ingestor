"""JSON extractor using built-in json module."""

import json
from pathlib import Path
from typing import Any

from ...types import ExtractionResult, MediaType
from ..base import BaseExtractor


class JsonExtractor(BaseExtractor):
    """Extract content from JSON files.

    Uses built-in json module for parsing.
    Converts JSON structure to readable markdown with code blocks.
    """

    media_type = MediaType.JSON

    async def extract(self, source: str | Path) -> ExtractionResult:
        """Extract content from a JSON file.

        Args:
            source: Path to the JSON file

        Returns:
            Extraction result with markdown representation
        """
        path = Path(source)

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        # Generate markdown representation
        markdown = self._json_to_markdown(data, path.stem)

        # Collect metadata
        metadata: dict[str, Any] = {
            "type": type(data).__name__,
        }
        if isinstance(data, list):
            metadata["item_count"] = len(data)
        elif isinstance(data, dict):
            metadata["key_count"] = len(data)
            metadata["keys"] = list(data.keys())[:20]  # First 20 keys

        return ExtractionResult(
            markdown=markdown,
            title=path.stem,
            source=str(path),
            media_type=MediaType.JSON,
            images=[],
            metadata=metadata,
        )

    def _json_to_markdown(self, data: Any, title: str) -> str:
        """Convert JSON data to markdown.

        Args:
            data: Parsed JSON data
            title: Document title

        Returns:
            Markdown representation
        """
        lines = [f"# {title}", ""]

        if isinstance(data, list):
            lines.append(f"**Type:** Array ({len(data)} items)")
            lines.append("")

            # If list of objects with consistent keys, try table format
            if self._is_tabular(data):
                lines.append(self._list_to_table(data))
            else:
                # Otherwise show as code block
                lines.append("```json")
                lines.append(json.dumps(data, indent=2, ensure_ascii=False))
                lines.append("```")

        elif isinstance(data, dict):
            lines.append(f"**Type:** Object ({len(data)} keys)")
            lines.append("")

            # Show structure
            lines.append("## Structure")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(data, indent=2, ensure_ascii=False))
            lines.append("```")

        else:
            # Primitive value
            lines.append(f"**Value:** `{json.dumps(data)}`")

        return "\n".join(lines)

    def _is_tabular(self, data: list[Any]) -> bool:
        """Check if list can be represented as a table.

        Args:
            data: List to check

        Returns:
            True if all items are dicts with same keys
        """
        if not data or len(data) > 100:  # Don't make huge tables
            return False

        if not all(isinstance(item, dict) for item in data):
            return False

        # Check if all have the same keys
        first_keys = set(data[0].keys())
        return all(set(item.keys()) == first_keys for item in data)

    def _list_to_table(self, data: list[Any]) -> str:
        """Convert list of dicts to markdown table.

        Args:
            data: List of dicts with same keys

        Returns:
            Markdown table
        """
        if not data:
            return ""

        headers = list(data[0].keys())
        header_row = "| " + " | ".join(str(h) for h in headers) + " |"
        separator = "| " + " | ".join("---" for _ in headers) + " |"

        rows = [header_row, separator]
        for item in data:
            cells = []
            for h in headers:
                val = item.get(h, "")
                if isinstance(val, (dict, list)):
                    val = json.dumps(val)
                cells.append(str(val).replace("|", "\\|").replace("\n", " "))
            rows.append("| " + " | ".join(cells) + " |")

        return "\n".join(rows)

    def supports(self, source: str | Path) -> bool:
        """Check if this extractor handles the source.

        Args:
            source: Path to check

        Returns:
            True if this is a JSON file
        """
        return str(source).lower().endswith(".json")
