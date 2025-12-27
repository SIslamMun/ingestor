"""Tests for ImageConverter."""

from io import BytesIO

import pytest

from ingestor.images.converter import ImageConverter
from ingestor.types import ExtractedImage


def create_test_image(format: str = "png", size: tuple = (10, 10), mode: str = "RGB") -> bytes:
    """Create a minimal test image."""
    from PIL import Image

    img = Image.new(mode, size, color=(255, 0, 0))
    buffer = BytesIO()
    img.save(buffer, format=format.upper())
    return buffer.getvalue()


class TestImageConverter:
    """Tests for ImageConverter class."""

    def test_init_default_format(self):
        """Test default target format is PNG."""
        converter = ImageConverter()
        assert converter.target_format == "png"

    def test_init_custom_format(self):
        """Test custom target format."""
        converter = ImageConverter(target_format="jpeg")
        assert converter.target_format == "jpeg"

    def test_no_conversion_needed(self):
        """Test that PNG→PNG is a no-op."""
        converter = ImageConverter(target_format="png")
        image = ExtractedImage(
            filename="test.png",
            data=create_test_image("png"),
            format="png",
        )

        result = converter.convert(image)

        assert result is image  # Same object, no conversion

    def test_jpeg_to_png(self):
        """Test JPEG to PNG conversion."""
        converter = ImageConverter(target_format="png")
        image = ExtractedImage(
            filename="test.jpg",
            data=create_test_image("jpeg"),
            format="jpeg",
        )

        result = converter.convert(image)

        assert result.format == "png"
        assert result.filename == "test.png"
        assert result.data != image.data  # Different data

    def test_png_to_jpeg_rgba(self):
        """Test PNG (RGBA) to JPEG conversion handles transparency."""
        converter = ImageConverter(target_format="jpeg")
        image = ExtractedImage(
            filename="test.png",
            data=create_test_image("png", mode="RGBA"),
            format="png",
        )

        result = converter.convert(image)

        assert result.format == "jpeg"
        # Should not raise on RGBA conversion

    def test_preserves_metadata(self):
        """Test that metadata is preserved after conversion."""
        converter = ImageConverter(target_format="png")
        image = ExtractedImage(
            filename="test.jpg",
            data=create_test_image("jpeg"),
            format="jpeg",
            page=5,
            caption="Test caption",
            context="Test context",
        )

        result = converter.convert(image)

        assert result.page == 5
        assert result.caption == "Test caption"
        assert result.context == "Test context"

    def test_convert_all(self):
        """Test batch conversion."""
        converter = ImageConverter(target_format="png")
        images = [
            ExtractedImage(
                filename=f"test{i}.jpg",
                data=create_test_image("jpeg"),
                format="jpeg",
            )
            for i in range(3)
        ]

        results = converter.convert_all(images)

        assert len(results) == 3
        for result in results:
            assert result.format == "png"

    def test_should_convert(self):
        """Test should_convert check."""
        converter = ImageConverter(target_format="png")

        png_image = ExtractedImage(filename="a.png", data=b"", format="png")
        jpg_image = ExtractedImage(filename="b.jpg", data=b"", format="jpeg")

        assert not converter.should_convert(png_image)
        assert converter.should_convert(jpg_image)


class TestImageConverterFormats:
    """Test various format conversions."""

    @pytest.mark.parametrize("source_format", ["png", "jpeg", "gif", "bmp"])
    def test_convert_to_png(self, source_format):
        """Test converting various formats to PNG."""
        converter = ImageConverter(target_format="png")
        image = ExtractedImage(
            filename=f"test.{source_format}",
            data=create_test_image(source_format if source_format != "jpeg" else "jpeg"),
            format=source_format,
        )

        result = converter.convert(image)

        if source_format == "png":
            assert result is image
        else:
            assert result.format == "png"
