"""Integration tests for image extraction."""


import pytest

from ingestor.extractors.image import ImageExtractor
from ingestor.types import MediaType


class TestImageExtraction:
    """Integration tests for image extraction."""

    @pytest.fixture
    def extractor(self):
        return ImageExtractor()

    @pytest.mark.asyncio
    async def test_extract_png(self, extractor, sample_png):
        """Test extracting PNG image."""
        if not sample_png.exists():
            pytest.skip("Fixture not generated")

        result = await extractor.extract(sample_png)

        assert result.media_type == MediaType.IMAGE
        assert result.markdown
        # Should have image dimensions
        assert "100" in result.markdown or "Dimensions" in result.markdown
        # Should have the image as extracted image
        assert len(result.images) == 1
        assert result.images[0].format in ("png", "PNG")

    @pytest.mark.asyncio
    async def test_extract_jpg(self, extractor, sample_jpg):
        """Test extracting JPEG image."""
        if not sample_jpg.exists():
            pytest.skip("Fixture not generated")

        result = await extractor.extract(sample_jpg)

        assert result.media_type == MediaType.IMAGE
        assert len(result.images) == 1
        assert result.images[0].format in ("jpeg", "jpg", "JPEG")

    @pytest.mark.asyncio
    async def test_image_metadata(self, extractor, sample_png):
        """Test image metadata extraction."""
        if not sample_png.exists():
            pytest.skip("Fixture not generated")

        result = await extractor.extract(sample_png)

        assert "width" in result.metadata
        assert "height" in result.metadata
        assert "format" in result.metadata
