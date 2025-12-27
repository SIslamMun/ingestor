"""Integration tests for data format extraction."""

import pytest

from ingestor.extractors.data import JsonExtractor
from ingestor.types import MediaType

# Check if defusedxml is available
try:
    import defusedxml
    DEFUSEDXML_AVAILABLE = True
except ImportError:
    DEFUSEDXML_AVAILABLE = False


class TestJsonExtraction:
    """Integration tests for JSON extraction."""

    @pytest.fixture
    def extractor(self):
        return JsonExtractor()

    @pytest.mark.asyncio
    async def test_extract_json_object(self, extractor, sample_json):
        """Test extracting JSON object file."""
        if not sample_json.exists():
            pytest.skip("Fixture not generated")

        result = await extractor.extract(sample_json)

        assert result.media_type == MediaType.JSON
        assert result.markdown
        # Should contain structured content
        assert "title" in result.markdown.lower() or "Test Document" in result.markdown

    @pytest.mark.asyncio
    async def test_extract_json_array(self, extractor, sample_json_array):
        """Test extracting tabular JSON array."""
        if not sample_json_array.exists():
            pytest.skip("Fixture not generated")

        result = await extractor.extract(sample_json_array)

        assert result.media_type == MediaType.JSON
        # Should be formatted as a table
        assert "|" in result.markdown


class TestXmlExtraction:
    """Integration tests for XML extraction."""

    @pytest.fixture
    def extractor(self):
        if not DEFUSEDXML_AVAILABLE:
            pytest.skip("defusedxml not installed")
        from ingestor.extractors.data import XmlExtractor
        return XmlExtractor()

    @pytest.mark.asyncio
    async def test_extract_xml(self, extractor, sample_xml):
        """Test extracting XML file."""
        if not sample_xml.exists():
            pytest.skip("Fixture not generated")

        result = await extractor.extract(sample_xml)

        assert result.media_type == MediaType.XML
        assert result.markdown
        # Should show XML structure
        assert "root" in result.markdown.lower() or "<" in result.markdown


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
        # Should be a markdown table
        assert "|" in result.markdown
        # Should have header row
        assert "name" in result.markdown.lower()
