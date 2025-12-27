"""Integration tests for archive extraction."""

import json
import zipfile

import pytest

from ingestor.core.registry import create_default_registry
from ingestor.types import MediaType


class TestZipExtraction:
    """Integration tests for ZIP archive extraction."""

    @pytest.fixture
    def extractor(self):
        from ingestor.extractors.archive import ZipExtractor
        registry = create_default_registry()
        return ZipExtractor(registry=registry)

    @pytest.fixture
    def sample_zip_with_content(self, tmp_path):
        """Create a ZIP with known content for testing."""
        zip_path = tmp_path / "test_archive.zip"

        with zipfile.ZipFile(zip_path, "w") as zf:
            # Add a text file
            zf.writestr("readme.txt", "This is the readme content.")
            # Add a JSON file
            zf.writestr("data.json", json.dumps({"key": "value", "count": 42}))
            # Add a nested file
            zf.writestr("folder/nested.txt", "Nested file content here.")

        return zip_path

    def test_supports_zip(self, extractor):
        """Test supports .zip files."""
        assert extractor.supports("archive.zip")
        assert extractor.supports("/path/to/archive.zip")
        assert not extractor.supports("archive.tar.gz")

    @pytest.mark.asyncio
    async def test_extract_zip(self, extractor, sample_zip_with_content):
        """Test extracting ZIP archive."""
        result = await extractor.extract(sample_zip_with_content)

        assert result.media_type == MediaType.ZIP
        assert result.markdown
        # Should contain content from files inside
        assert "readme" in result.markdown.lower() or "This is the readme" in result.markdown

    @pytest.mark.asyncio
    async def test_zip_processes_all_files(self, extractor, sample_zip_with_content):
        """Test ZIP processes all supported files."""
        result = await extractor.extract(sample_zip_with_content)

        # Should have processed multiple files
        assert result.metadata.get("file_count", 0) >= 2
        assert result.metadata.get("processed_count", 0) >= 1

    @pytest.mark.asyncio
    async def test_zip_nested_files(self, extractor, sample_zip_with_content):
        """Test ZIP handles nested files."""
        result = await extractor.extract(sample_zip_with_content)

        # Should include nested content
        assert "nested" in result.markdown.lower() or "folder" in result.markdown.lower()

    @pytest.mark.asyncio
    async def test_zip_with_json(self, extractor, sample_zip_with_content):
        """Test ZIP handles mixed file types."""
        result = await extractor.extract(sample_zip_with_content)

        # Should have processed multiple files
        assert result.metadata.get("file_count", 0) >= 2
        # Should have some content extracted
        assert len(result.markdown) > 100


class TestZipWithImages:
    """Tests for ZIP archives containing images."""

    @pytest.fixture
    def extractor(self):
        from ingestor.extractors.archive import ZipExtractor
        registry = create_default_registry()
        return ZipExtractor(registry=registry)

    @pytest.fixture
    def zip_with_image(self, tmp_path, sample_png):
        """Create ZIP containing an image."""
        if not sample_png.exists():
            pytest.skip("Image fixture not generated")

        zip_path = tmp_path / "images.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(sample_png, "image.png")
            zf.writestr("info.txt", "Archive with image")

        return zip_path

    @pytest.mark.asyncio
    async def test_zip_extracts_images(self, extractor, zip_with_image):
        """Test ZIP extracts images from contained files."""
        result = await extractor.extract(zip_with_image)

        # Should have extracted images
        assert len(result.images) >= 1 or result.metadata.get("image_count", 0) >= 1
