"""Tests for JsonExtractor."""

import json
from pathlib import Path

import pytest

from ingestor.extractors.data.json_extractor import JsonExtractor
from ingestor.types import MediaType


class TestJsonExtractor:
    """Tests for JsonExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create a JsonExtractor instance."""
        return JsonExtractor()

    def test_media_type(self, extractor):
        """Test media type is correct."""
        assert extractor.media_type == MediaType.JSON

    def test_supports_json(self, extractor):
        """Test supports .json files."""
        assert extractor.supports("file.json")
        assert extractor.supports("/path/to/file.json")
        assert extractor.supports(Path("file.json"))

    def test_does_not_support_other(self, extractor):
        """Test does not support other extensions."""
        assert not extractor.supports("file.txt")
        assert not extractor.supports("file.xml")

    @pytest.mark.asyncio
    async def test_extract_object(self, extractor, tmp_path):
        """Test extracting JSON object."""
        data = {"name": "Test", "value": 42}
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(data))

        result = await extractor.extract(json_file)

        assert result.media_type == MediaType.JSON
        assert "Test" in result.markdown
        assert "42" in result.markdown
        assert result.metadata["type"] == "dict"

    @pytest.mark.asyncio
    async def test_extract_array_tabular(self, extractor, tmp_path):
        """Test extracting tabular JSON array."""
        data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(data))

        result = await extractor.extract(json_file)

        assert result.media_type == MediaType.JSON
        # Should be formatted as table
        assert "|" in result.markdown
        assert "Alice" in result.markdown
        assert "Bob" in result.markdown

    @pytest.mark.asyncio
    async def test_extract_nested(self, extractor, tmp_path):
        """Test extracting nested JSON."""
        data = {
            "root": {
                "child": {"value": 1}
            }
        }
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(data))

        result = await extractor.extract(json_file)

        assert "root" in result.markdown
        assert "child" in result.markdown


class TestJsonExtractorHelpers:
    """Tests for JsonExtractor helper methods."""

    @pytest.fixture
    def extractor(self):
        return JsonExtractor()

    def test_is_tabular_with_uniform_dicts(self, extractor):
        """Test _is_tabular with uniform dict array."""
        data = [
            {"a": 1, "b": 2},
            {"a": 3, "b": 4},
        ]
        assert extractor._is_tabular(data)

    def test_is_tabular_with_mixed_keys(self, extractor):
        """Test _is_tabular with non-uniform dicts."""
        data = [
            {"a": 1, "b": 2},
            {"a": 3, "c": 4},  # Different keys
        ]
        assert not extractor._is_tabular(data)

    def test_is_tabular_with_non_dicts(self, extractor):
        """Test _is_tabular with non-dict items."""
        data = [1, 2, 3]
        assert not extractor._is_tabular(data)

    def test_is_tabular_empty_list(self, extractor):
        """Test _is_tabular with empty list."""
        assert not extractor._is_tabular([])

    def test_is_tabular_large_list(self, extractor):
        """Test _is_tabular skips very large lists."""
        data = [{"a": i} for i in range(200)]
        assert not extractor._is_tabular(data)  # Over 100 limit

    def test_list_to_table(self, extractor):
        """Test _list_to_table conversion."""
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        table = extractor._list_to_table(data)

        assert "| name | age |" in table or "| age | name |" in table
        assert "Alice" in table
        assert "30" in table
