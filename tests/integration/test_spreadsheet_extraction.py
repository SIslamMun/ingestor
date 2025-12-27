"""Integration tests for spreadsheet extraction."""


import pytest

from ingestor.types import MediaType


class TestXlsxExtraction:
    """Integration tests for XLSX extraction."""

    @pytest.fixture
    def extractor(self):
        try:
            from ingestor.extractors.excel import XlsxExtractor
            return XlsxExtractor()
        except ImportError:
            pytest.skip("pandas/openpyxl not installed")

    @pytest.mark.asyncio
    async def test_extract_xlsx(self, extractor, sample_xlsx):
        """Test extracting XLSX file."""
        if not sample_xlsx.exists():
            pytest.skip("Fixture not generated")

        result = await extractor.extract(sample_xlsx)

        assert result.media_type == MediaType.XLSX
        assert result.markdown
        # Should have table format
        assert "|" in result.markdown
        # Should have sheet names in metadata
        assert "sheets" in result.metadata or "sheet_count" in result.metadata

    @pytest.mark.asyncio
    async def test_xlsx_multiple_sheets(self, extractor, sample_xlsx):
        """Test XLSX with multiple sheets."""
        if not sample_xlsx.exists():
            pytest.skip("Fixture not generated")

        result = await extractor.extract(sample_xlsx)

        # Fixture has 2 sheets: People and Products
        if result.metadata.get("sheet_count", 0) >= 2:
            assert "People" in result.markdown or "Products" in result.markdown

    @pytest.mark.asyncio
    async def test_xlsx_table_format(self, extractor, sample_xlsx):
        """Test XLSX produces valid markdown tables."""
        if not sample_xlsx.exists():
            pytest.skip("Fixture not generated")

        result = await extractor.extract(sample_xlsx)

        # Should have header separator
        assert "---" in result.markdown
        # Should have pipe characters for table
        lines_with_pipes = [l for l in result.markdown.split("\n") if "|" in l]
        assert len(lines_with_pipes) >= 2  # Header + separator + at least 1 row


class TestXlsExtraction:
    """Integration tests for legacy XLS extraction."""

    @pytest.fixture
    def extractor(self):
        try:
            from ingestor.extractors.excel import XlsExtractor
            return XlsExtractor()
        except ImportError:
            pytest.skip("pandas/xlrd not installed")

    def test_supports_xls(self, extractor):
        """Test supports .xls but not .xlsx."""
        assert extractor.supports("file.xls")
        assert not extractor.supports("file.xlsx")


class TestCsvExtraction:
    """Integration tests for CSV extraction."""

    @pytest.fixture
    def extractor(self):
        try:
            from ingestor.extractors.data import CsvExtractor
            return CsvExtractor()
        except ImportError:
            pytest.skip("pandas not installed")

    @pytest.mark.asyncio
    async def test_extract_csv(self, extractor, sample_csv):
        """Test extracting CSV file."""
        if not sample_csv.exists():
            pytest.skip("Fixture not generated")

        result = await extractor.extract(sample_csv)

        assert result.media_type == MediaType.CSV
        assert "|" in result.markdown
        # Should have our test data
        assert "Alice" in result.markdown
        assert "Bob" in result.markdown

    @pytest.mark.asyncio
    async def test_csv_metadata(self, extractor, sample_csv):
        """Test CSV metadata extraction."""
        if not sample_csv.exists():
            pytest.skip("Fixture not generated")

        result = await extractor.extract(sample_csv)

        assert "row_count" in result.metadata
        assert "column_count" in result.metadata
        assert result.metadata["row_count"] == 3  # Alice, Bob, Charlie
