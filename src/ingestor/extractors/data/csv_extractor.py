"""CSV extractor using pandas."""

from pathlib import Path

from ...types import ExtractionResult, MediaType
from ..base import BaseExtractor


class CsvExtractor(BaseExtractor):
    """Extract content from CSV files.

    Uses pandas for reading with automatic delimiter detection.
    Converts to a markdown table.
    """

    media_type = MediaType.CSV

    async def extract(self, source: str | Path) -> ExtractionResult:
        """Extract content from a CSV file.

        Args:
            source: Path to the CSV file

        Returns:
            Extraction result with markdown table
        """
        import pandas as pd

        path = Path(source)

        # Try to read with automatic delimiter detection
        try:
            df = pd.read_csv(path, sep=None, engine="python")
        except Exception:
            # Fallback to comma delimiter
            df = pd.read_csv(path)

        # Convert to markdown table
        markdown = self._df_to_markdown(df)

        return ExtractionResult(
            markdown=markdown,
            title=path.stem,
            source=str(path),
            media_type=MediaType.CSV,
            images=[],
            metadata={
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
            },
        )

    def _df_to_markdown(self, df) -> str:
        """Convert a DataFrame to a markdown table.

        Args:
            df: pandas DataFrame

        Returns:
            Markdown table string
        """
        import pandas as pd

        if df.empty:
            return ""

        # Get column headers
        headers = list(df.columns)
        header_row = "| " + " | ".join(str(h) for h in headers) + " |"
        separator = "| " + " | ".join("---" for _ in headers) + " |"

        # Build data rows
        rows = [header_row, separator]
        for _, row in df.iterrows():
            cells = []
            for val in row:
                # Handle NaN and escape pipes
                if pd.isna(val):
                    cells.append("")
                else:
                    cells.append(str(val).replace("|", "\\|").replace("\n", " "))
            rows.append("| " + " | ".join(cells) + " |")

        return "\n".join(rows)

    def supports(self, source: str | Path) -> bool:
        """Check if this extractor handles the source.

        Args:
            source: Path to check

        Returns:
            True if this is a CSV file
        """
        return str(source).lower().endswith(".csv")
