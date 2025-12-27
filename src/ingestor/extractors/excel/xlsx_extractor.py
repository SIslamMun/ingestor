"""Modern Excel (XLSX) extractor using pandas and openpyxl."""

from pathlib import Path

from ...types import ExtractionResult, MediaType
from ..base import BaseExtractor


class XlsxExtractor(BaseExtractor):
    """Extract content from modern Excel files (XLSX).

    Uses pandas with openpyxl backend for reading.
    Converts each sheet to a markdown table.
    """

    media_type = MediaType.XLSX

    async def extract(self, source: str | Path) -> ExtractionResult:
        """Extract content from an XLSX file.

        Args:
            source: Path to the XLSX file

        Returns:
            Extraction result with markdown tables
        """
        import pandas as pd

        path = Path(source)

        # Read all sheets
        xlsx = pd.ExcelFile(path, engine="openpyxl")
        sheets_md = []

        for sheet_name in xlsx.sheet_names:
            df = pd.read_excel(xlsx, sheet_name=sheet_name)

            # Skip empty sheets
            if df.empty:
                continue

            # Build markdown for this sheet
            sheet_lines = [f"## {sheet_name}", ""]

            # Convert DataFrame to markdown table
            table_md = self._df_to_markdown(df)
            sheet_lines.append(table_md)

            sheets_md.append("\n".join(sheet_lines))

        markdown = "\n\n---\n\n".join(sheets_md)

        return ExtractionResult(
            markdown=markdown,
            title=path.stem,
            source=str(path),
            media_type=MediaType.XLSX,
            images=[],  # Excel doesn't extract images in this implementation
            metadata={
                "sheet_count": len(xlsx.sheet_names),
                "sheets": xlsx.sheet_names,
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
                    cells.append(str(val).replace("|", "\\|"))
            rows.append("| " + " | ".join(cells) + " |")

        return "\n".join(rows)

    def supports(self, source: str | Path) -> bool:
        """Check if this extractor handles the source.

        Args:
            source: Path to check

        Returns:
            True if this is an XLSX file
        """
        return str(source).lower().endswith(".xlsx")
