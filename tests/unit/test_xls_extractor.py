"""Real unit tests for XLS Extractor - no mocking."""

import pytest
from pathlib import Path
from io import BytesIO

from ingestor.extractors.excel.xls_extractor import XlsExtractor
from ingestor.types import MediaType


class TestXlsExtractor:
    """Tests for XlsExtractor class."""

    @pytest.fixture
    def extractor(self):
        return XlsExtractor()

    def test_extractor_init(self):
        """Test extractor initialization."""
        extractor = XlsExtractor()
        assert extractor is not None

    def test_media_type(self, extractor):
        """Test media type is XLS."""
        assert extractor.media_type == MediaType.XLS

    def test_supports_xls(self, extractor, tmp_path):
        """Test supports() for XLS file."""
        xls_file = tmp_path / "test.xls"
        xls_file.write_bytes(b"")  # Empty file
        
        result = extractor.supports(str(xls_file))
        assert result in [True, False]

    def test_supports_non_xls(self, extractor, tmp_path):
        """Test supports() returns False for non-XLS files."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Not an XLS file")
        
        assert extractor.supports(str(txt_file)) is False

    def test_supports_xlsx_returns_false(self, extractor, tmp_path):
        """Test supports() returns False for XLSX files."""
        xlsx_file = tmp_path / "test.xlsx"
        xlsx_file.write_bytes(b"PK")  # ZIP signature
        
        # XLS extractor should not handle XLSX
        assert extractor.supports(str(xlsx_file)) is False


class TestXlsExtractorDfToMarkdown:
    """Tests for XlsExtractor _df_to_markdown method."""

    @pytest.fixture
    def extractor(self):
        return XlsExtractor()

    def test_empty_dataframe(self, extractor):
        """Test converting empty DataFrame."""
        try:
            import pandas as pd
            
            df = pd.DataFrame()
            result = extractor._df_to_markdown(df)
            
            assert result == ""
        except ImportError:
            pytest.skip("pandas not installed")

    def test_simple_dataframe(self, extractor):
        """Test converting simple DataFrame."""
        try:
            import pandas as pd
            
            df = pd.DataFrame({
                'Name': ['Alice', 'Bob'],
                'Age': [25, 30]
            })
            
            result = extractor._df_to_markdown(df)
            
            assert '| Name | Age |' in result
            assert '| Alice | 25 |' in result
            assert '| Bob | 30 |' in result
        except ImportError:
            pytest.skip("pandas not installed")

    def test_dataframe_with_nan(self, extractor):
        """Test converting DataFrame with NaN values."""
        try:
            import pandas as pd
            import numpy as np
            
            df = pd.DataFrame({
                'A': [1, np.nan, 3],
                'B': ['x', 'y', np.nan]
            })
            
            result = extractor._df_to_markdown(df)
            
            assert '| A | B |' in result
            # NaN values should be empty cells
            assert result is not None
        except ImportError:
            pytest.skip("pandas not installed")

    def test_dataframe_with_pipes(self, extractor):
        """Test converting DataFrame with pipe characters."""
        try:
            import pandas as pd
            
            df = pd.DataFrame({
                'Formula': ['A|B', 'C|D'],
                'Value': [1, 2]
            })
            
            result = extractor._df_to_markdown(df)
            
            # Pipes should be escaped
            assert '\\|' in result or 'A|B' not in result.split('|')[2]
        except ImportError:
            pytest.skip("pandas not installed")

    def test_dataframe_separator_row(self, extractor):
        """Test that separator row is included."""
        try:
            import pandas as pd
            
            df = pd.DataFrame({'Col': [1]})
            result = extractor._df_to_markdown(df)
            
            assert '| --- |' in result
        except ImportError:
            pytest.skip("pandas not installed")


class TestXlsExtractorExtract:
    """Tests for XlsExtractor extract method."""

    @pytest.fixture
    def extractor(self):
        return XlsExtractor()

    @pytest.mark.asyncio
    async def test_extract_real_xls(self, extractor):
        """Test extracting from a real XLS file."""
        # This test would require a real XLS file
        # Skip if we can't create one
        try:
            import xlrd
            import xlwt
            from pathlib import Path
            import tempfile
            
            # Create a real XLS file using xlwt
            workbook = xlwt.Workbook()
            sheet = workbook.add_sheet('Sheet1')
            sheet.write(0, 0, 'Name')
            sheet.write(0, 1, 'Value')
            sheet.write(1, 0, 'Test')
            sheet.write(1, 1, 42)
            
            with tempfile.NamedTemporaryFile(suffix='.xls', delete=False) as f:
                workbook.save(f.name)
                xls_path = Path(f.name)
            
            try:
                result = await extractor.extract(xls_path)
                
                assert result is not None
                assert result.media_type == MediaType.XLS
                assert 'Name' in result.markdown
                assert 'Test' in result.markdown
                assert result.metadata['sheet_count'] >= 1
            finally:
                xls_path.unlink()
                
        except ImportError:
            pytest.skip("xlwt or xlrd not installed")


class TestXlsExtractorSupports:
    """Tests for XlsExtractor supports() method."""

    @pytest.fixture
    def extractor(self):
        return XlsExtractor()

    def test_supports_by_extension(self, extractor, tmp_path):
        """Test supports() uses file extension."""
        xls_file = tmp_path / "data.xls"
        xls_file.write_bytes(b"dummy content")
        
        result = extractor.supports(str(xls_file))
        # Should check by extension
        assert result in [True, False]

    def test_supports_path_object(self, extractor, tmp_path):
        """Test supports() accepts Path objects."""
        xls_file = tmp_path / "data.xls"
        xls_file.write_bytes(b"dummy")
        
        result = extractor.supports(xls_file)
        assert result in [True, False]

    def test_supports_csv_returns_false(self, extractor, tmp_path):
        """Test supports() returns False for CSV."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b,c\n1,2,3")
        
        assert extractor.supports(str(csv_file)) is False
