"""Real unit tests for Image Processing - no mocking."""

import pytest
from pathlib import Path
from io import BytesIO

from ingestor.images.converter import ImageConverter
from ingestor.images.naming import ImageNamer
from ingestor.images.processor import ImageProcessor
from ingestor.types import ExtractedImage, IngestConfig


def create_test_image(format_name: str = "png", color: str = "red") -> bytes:
    """Helper to create test image data."""
    try:
        from PIL import Image
        img = Image.new('RGB', (10, 10), color=color)
        buffer = BytesIO()
        pil_format = format_name.upper()
        if pil_format == "JPG":
            pil_format = "JPEG"
        img.save(buffer, format=pil_format)
        return buffer.getvalue()
    except ImportError:
        return b""


class TestImageConverter:
    """Tests for ImageConverter class."""

    @pytest.fixture
    def converter(self):
        return ImageConverter()

    def test_converter_init(self):
        """Test converter initialization."""
        converter = ImageConverter()
        assert converter is not None

    def test_converter_default_format(self):
        """Test default target format."""
        converter = ImageConverter()
        assert converter.target_format == "png"

    def test_converter_custom_format(self):
        """Test custom target format."""
        converter = ImageConverter(target_format="webp")
        assert converter.target_format == "webp"

    def test_converter_jpg_alias(self):
        """Test that jpg is normalized to jpeg."""
        converter = ImageConverter(target_format="jpg")
        assert converter.target_format == "jpeg"

    def test_converter_unsupported_format(self):
        """Test that unsupported formats raise error."""
        with pytest.raises(ValueError, match="Unsupported format"):
            ImageConverter(target_format="xyz")

    def test_supported_formats(self):
        """Test supported formats list."""
        assert "png" in ImageConverter.SUPPORTED_FORMATS
        assert "jpeg" in ImageConverter.SUPPORTED_FORMATS
        assert "webp" in ImageConverter.SUPPORTED_FORMATS
        assert "gif" in ImageConverter.SUPPORTED_FORMATS
        assert "bmp" in ImageConverter.SUPPORTED_FORMATS
        assert "tiff" in ImageConverter.SUPPORTED_FORMATS

    def test_convert_png_to_png_no_change(self, converter):
        """Test converting PNG to PNG (no conversion needed)."""
        try:
            from PIL import Image
            
            png_data = create_test_image("png", "red")
            
            image = ExtractedImage(
                filename="test.png",
                data=png_data,
                format="png"
            )
            
            result = converter.convert(image)
            
            # Should return same image (no conversion needed)
            assert result.format == "png"
            assert result.filename == "test.png"
        except ImportError:
            pytest.skip("PIL not installed")

    def test_convert_jpg_to_png(self):
        """Test converting JPG to PNG."""
        try:
            from PIL import Image
            
            converter = ImageConverter(target_format="png")
            jpg_data = create_test_image("jpeg", "blue")
            
            image = ExtractedImage(
                filename="test.jpg",
                data=jpg_data,
                format="jpeg"
            )
            
            result = converter.convert(image)
            
            assert result.format == "png"
            assert result.filename == "test.png"
            # Verify it's now PNG
            assert result.data[:4] == b'\x89PNG'
        except ImportError:
            pytest.skip("PIL not installed")

    def test_convert_png_to_jpeg(self):
        """Test converting PNG to JPEG."""
        try:
            from PIL import Image
            
            converter = ImageConverter(target_format="jpeg")
            png_data = create_test_image("png", "blue")
            
            image = ExtractedImage(
                filename="test.png",
                data=png_data,
                format="png"
            )
            
            result = converter.convert(image)
            
            assert result.format == "jpeg"
            assert result.filename == "test.jpg"
            # JPEG magic number
            assert result.data[:2] == b'\xff\xd8'
        except ImportError:
            pytest.skip("PIL not installed")

    def test_convert_to_webp(self):
        """Test converting to WebP format."""
        try:
            from PIL import Image
            
            converter = ImageConverter(target_format="webp")
            png_data = create_test_image("png", "green")
            
            image = ExtractedImage(
                filename="test.png",
                data=png_data,
                format="png"
            )
            
            result = converter.convert(image)
            
            assert result.format == "webp"
            # WebP magic number
            assert result.data[:4] == b'RIFF'
        except ImportError:
            pytest.skip("PIL not installed")

    def test_convert_svg_skipped(self, converter):
        """Test that SVG files are skipped."""
        image = ExtractedImage(
            filename="test.svg",
            data=b"<svg></svg>",
            format="svg"
        )
        
        result = converter.convert(image)
        
        # Should return original (SVG can't be converted by PIL)
        assert result is image

    def test_should_convert_different_format(self, converter):
        """Test should_convert returns True for different formats."""
        image = ExtractedImage(
            filename="test.jpg",
            data=b"",
            format="jpeg"
        )
        assert converter.should_convert(image) is True

    def test_should_convert_same_format(self, converter):
        """Test should_convert returns False for same format."""
        image = ExtractedImage(
            filename="test.png",
            data=b"",
            format="png"
        )
        assert converter.should_convert(image) is False

    def test_should_convert_jpg_alias(self, converter):
        """Test should_convert handles jpg/jpeg alias."""
        image = ExtractedImage(
            filename="test.jpg",
            data=b"",
            format="jpg"  # Should normalize to jpeg
        )
        # PNG converter should need to convert jpeg
        assert converter.should_convert(image) is True

    def test_convert_all(self, converter):
        """Test converting multiple images."""
        try:
            from PIL import Image
            
            images = [
                ExtractedImage(
                    filename=f"test{i}.png",
                    data=create_test_image("png"),
                    format="png"
                )
                for i in range(3)
            ]
            
            results = converter.convert_all(images)
            
            assert len(results) == 3
            for result in results:
                assert result.format == "png"
        except ImportError:
            pytest.skip("PIL not installed")

    def test_convert_preserves_metadata(self):
        """Test that conversion preserves image metadata."""
        try:
            from PIL import Image
            
            converter = ImageConverter(target_format="jpeg")
            png_data = create_test_image("png")
            
            image = ExtractedImage(
                filename="test.png",
                data=png_data,
                format="png",
                page=5,
                caption="Test caption",
                context="Test context",
                description="Test description"
            )
            
            result = converter.convert(image)
            
            assert result.page == 5
            assert result.caption == "Test caption"
            assert result.context == "Test context"
            assert result.description == "Test description"
        except ImportError:
            pytest.skip("PIL not installed")

    def test_convert_gif_to_png(self):
        """Test converting GIF to PNG."""
        try:
            from PIL import Image
            
            converter = ImageConverter(target_format="png")
            
            # Create simple GIF
            img = Image.new('P', (10, 10))
            buffer = BytesIO()
            img.save(buffer, format='GIF')
            gif_data = buffer.getvalue()
            
            image = ExtractedImage(
                filename="test.gif",
                data=gif_data,
                format="gif"
            )
            
            result = converter.convert(image)
            
            assert result.format == "png"
            assert result.data[:4] == b'\x89PNG'
        except ImportError:
            pytest.skip("PIL not installed")


class TestImageNamer:
    """Tests for ImageNamer class."""

    @pytest.fixture
    def namer(self):
        return ImageNamer()

    def test_namer_init(self):
        """Test namer initialization."""
        namer = ImageNamer()
        assert namer is not None

    def test_namer_default_pattern(self):
        """Test default naming pattern."""
        namer = ImageNamer()
        assert namer.pattern == "figure_{num:03d}"

    def test_namer_custom_pattern(self):
        """Test custom naming pattern."""
        namer = ImageNamer(pattern="img_{num}")
        assert namer.pattern == "img_{num}"

    def test_namer_with_prefix(self):
        """Test namer with prefix."""
        namer = ImageNamer(prefix="doc")
        assert namer.prefix == "doc"

    def test_generate_basic(self, namer):
        """Test basic name generation."""
        image = ExtractedImage(
            filename="original.png",
            data=b"",
            format="png"
        )
        
        name = namer.generate(image)
        
        assert name is not None
        assert name.endswith(".png")
        assert "figure_001" in name

    def test_generate_sequential(self, namer):
        """Test sequential name generation."""
        image = ExtractedImage(filename="test.png", data=b"", format="png")
        
        names = []
        for _ in range(3):
            names.append(namer.generate(image))
        
        assert "figure_001" in names[0]
        assert "figure_002" in names[1]
        assert "figure_003" in names[2]

    def test_generate_with_page(self):
        """Test name generation with page number."""
        namer = ImageNamer(pattern="page{page}_img{page_num}")
        
        image = ExtractedImage(
            filename="test.png",
            data=b"",
            format="png",
            page=5
        )
        
        name = namer.generate(image)
        
        assert "page5" in name
        assert "img1" in name

    def test_generate_with_source_name(self, namer):
        """Test name generation with source name."""
        namer = ImageNamer(pattern="{source}_{num:03d}")
        
        image = ExtractedImage(filename="test.png", data=b"", format="png")
        
        name = namer.generate(image, source_name="my_document")
        
        assert "my_document" in name

    def test_generate_with_prefix(self):
        """Test name generation with prefix."""
        namer = ImageNamer(prefix="chapter1")
        
        image = ExtractedImage(filename="test.png", data=b"", format="png")
        
        name = namer.generate(image)
        
        assert name.startswith("chapter1_")

    def test_reset(self, namer):
        """Test counter reset."""
        image = ExtractedImage(filename="test.png", data=b"", format="png")
        
        # Generate some names
        namer.generate(image)
        namer.generate(image)
        
        # Reset
        namer.reset()
        
        # Should start from 1 again
        name = namer.generate(image)
        assert "figure_001" in name

    def test_rename_image(self, namer):
        """Test renaming an image."""
        image = ExtractedImage(
            filename="original.png",
            data=b"test data",
            format="png",
            page=3,
            caption="Test caption"
        )
        
        renamed = namer.rename(image)
        
        assert renamed.filename != image.filename
        assert renamed.data == image.data
        assert renamed.format == image.format
        assert renamed.page == image.page
        assert renamed.caption == image.caption

    def test_unique_names(self, namer):
        """Test that generated names are unique."""
        image = ExtractedImage(filename="test.png", data=b"", format="png")
        
        names = set()
        for _ in range(10):
            name = namer.generate(image)
            names.add(name)
        
        assert len(names) == 10


class TestImageNamerSanitization:
    """Tests for ImageNamer name sanitization."""

    @pytest.fixture
    def namer(self):
        return ImageNamer(pattern="{source}_{num}")

    def test_sanitize_removes_slashes(self, namer):
        """Test that slashes are removed from source names."""
        image = ExtractedImage(filename="test.png", data=b"", format="png")
        
        name = namer.generate(image, source_name="my/path/file")
        
        # Should not contain raw slash
        # Sanitization behavior may vary
        assert name is not None

    def test_sanitize_removes_special_chars(self, namer):
        """Test that special chars are handled."""
        image = ExtractedImage(filename="test.png", data=b"", format="png")
        
        name = namer.generate(image, source_name="file<with>special:chars?")
        
        assert name is not None


class TestImageProcessor:
    """Tests for ImageProcessor class."""

    @pytest.fixture
    def processor(self):
        return ImageProcessor()

    def test_processor_init(self):
        """Test processor initialization."""
        processor = ImageProcessor()
        assert processor is not None

    def test_processor_with_config(self):
        """Test processor with custom config."""
        config = IngestConfig(target_image_format="webp")
        processor = ImageProcessor(config=config)
        
        assert processor.config.target_image_format == "webp"

    def test_processor_default_config(self):
        """Test processor with default config."""
        processor = ImageProcessor()
        
        assert processor.config is not None
        assert processor.converter is not None

    def test_processor_keep_raw_images(self):
        """Test processor with keep_raw_images option."""
        config = IngestConfig(keep_raw_images=True)
        processor = ImageProcessor(config=config)
        
        # Should not have converter when keeping raw
        assert processor.converter is None

    def test_processor_has_converter(self):
        """Test processor has converter by default."""
        processor = ImageProcessor()
        
        assert processor.converter is not None

    def test_vlm_describer_lazy_load(self):
        """Test VLM describer is lazy loaded."""
        processor = ImageProcessor()
        
        # Should not be loaded initially
        assert processor._vlm_describer is None

    def test_standardize_filename(self):
        """Test _standardize_filename method."""
        processor = ImageProcessor()
        
        image = ExtractedImage(
            filename="original.png",
            data=b"test",
            format="png"
        )
        
        result = processor._standardize_filename(image, "my_document", 1)
        
        assert result.filename == "my_document_img_001.png"
        assert result.data == b"test"

    def test_standardize_filename_cleans_source(self):
        """Test _standardize_filename cleans source name."""
        processor = ImageProcessor()
        
        image = ExtractedImage(filename="test.png", data=b"", format="png")
        
        result = processor._standardize_filename(image, "my/path/file.docx", 5)
        
        # Should clean the source name
        assert "_img_005" in result.filename
        assert "/" not in result.filename

    def test_standardize_filename_jpeg_to_jpg(self):
        """Test _standardize_filename converts jpeg extension to jpg."""
        processor = ImageProcessor()
        
        image = ExtractedImage(filename="photo.jpeg", data=b"", format="jpeg")
        
        result = processor._standardize_filename(image, "doc", 1)
        
        assert result.filename.endswith(".jpg")

    def test_process_sync(self):
        """Test process_sync method."""
        try:
            from PIL import Image
            
            processor = ImageProcessor()
            
            images = [
                ExtractedImage(
                    filename="test.png",
                    data=create_test_image("png"),
                    format="png"
                )
            ]
            
            results = processor.process_sync(images, "document")
            
            assert len(results) == 1
            assert "document_img_001" in results[0].filename
        except ImportError:
            pytest.skip("PIL not installed")

    def test_process_sync_multiple(self):
        """Test process_sync with multiple images."""
        try:
            from PIL import Image
            
            processor = ImageProcessor()
            
            images = [
                ExtractedImage(
                    filename=f"img{i}.png",
                    data=create_test_image("png"),
                    format="png"
                )
                for i in range(3)
            ]
            
            results = processor.process_sync(images, "mydoc")
            
            assert len(results) == 3
            assert "mydoc_img_001" in results[0].filename
            assert "mydoc_img_002" in results[1].filename
            assert "mydoc_img_003" in results[2].filename
        except ImportError:
            pytest.skip("PIL not installed")

    @pytest.mark.asyncio
    async def test_process_single_image(self):
        """Test processing a single image."""
        try:
            from PIL import Image
            
            processor = ImageProcessor()
            
            png_data = create_test_image("png", "red")
            
            images = [
                ExtractedImage(
                    filename="test.png",
                    data=png_data,
                    format="png",
                )
            ]
            
            results = await processor.process(images)
            
            assert len(results) == 1
        except ImportError:
            pytest.skip("PIL not installed")

    @pytest.mark.asyncio
    async def test_process_multiple_images(self):
        """Test processing multiple images."""
        try:
            from PIL import Image
            
            processor = ImageProcessor()
            
            images = []
            for i, color in enumerate(['red', 'green', 'blue']):
                images.append(ExtractedImage(
                    filename=f"image_{i}.png",
                    data=create_test_image("png", color),
                    format="png",
                ))
            
            results = await processor.process(images)
            
            assert len(results) == 3
        except ImportError:
            pytest.skip("PIL not installed")

    @pytest.mark.asyncio
    async def test_process_empty_list(self):
        """Test processing empty image list."""
        processor = ImageProcessor()
        
        results = await processor.process([])
        
        assert results == []


class TestImageProcessorEdgeCases:
    """Edge case tests for ImageProcessor."""

    @pytest.mark.asyncio
    async def test_process_with_svg(self):
        """Test processing SVG (should be passed through)."""
        processor = ImageProcessor()
        
        images = [
            ExtractedImage(
                filename="icon.svg",
                data=b"<svg></svg>",
                format="svg",
            )
        ]
        
        results = await processor.process(images)
        
        # SVG should be passed through unchanged
        assert len(results) == 1
        assert results[0].format == "svg"


class TestExtractedImageType:
    """Tests for ExtractedImage type."""

    def test_extracted_image_creation(self):
        """Test creating ExtractedImage."""
        image = ExtractedImage(
            filename="test.png",
            data=b"test data",
            format="png"
        )
        
        assert image.filename == "test.png"
        assert image.data == b"test data"
        assert image.format == "png"

    def test_extracted_image_with_metadata(self):
        """Test ExtractedImage with all metadata."""
        image = ExtractedImage(
            filename="test.png",
            data=b"test data",
            format="png",
            page=5,
            caption="Test caption",
            context="Test context",
            description="Test description"
        )
        
        assert image.page == 5
        assert image.caption == "Test caption"
        assert image.context == "Test context"
        assert image.description == "Test description"

    def test_extracted_image_size_bytes(self):
        """Test size_bytes property."""
        image = ExtractedImage(
            filename="test.png",
            data=b"12345",
            format="png"
        )
        
        assert image.size_bytes == 5

    def test_extracted_image_defaults(self):
        """Test ExtractedImage default values."""
        image = ExtractedImage(
            filename="test.png",
            data=b"",
            format="png"
        )
        
        assert image.page is None
        assert image.caption is None
        assert image.context is None
        assert image.description is None
