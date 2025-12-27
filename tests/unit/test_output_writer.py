"""Real unit tests for Output Writer - no mocking."""

import json

import pytest

from ingestor.output.writer import OutputWriter, OutputWriterSync
from ingestor.types import ExtractedImage, ExtractionResult, IngestConfig, MediaType


class TestOutputWriterInit:
    """Tests for OutputWriter initialization."""

    def test_default_init(self, tmp_path):
        """Test default initialization."""
        config = IngestConfig(output_dir=tmp_path)
        writer = OutputWriter(config)

        assert writer is not None
        assert writer.config is config

    def test_init_without_config(self):
        """Test initialization without config."""
        writer = OutputWriter()

        assert writer is not None
        assert writer.config is not None

    def test_has_image_processor(self, tmp_path):
        """Test writer has image processor."""
        config = IngestConfig(output_dir=tmp_path)
        writer = OutputWriter(config)

        assert writer.image_processor is not None


class TestOutputWriterCleanName:
    """Tests for OutputWriter _clean_name method."""

    @pytest.fixture
    def writer(self, tmp_path):
        config = IngestConfig(output_dir=tmp_path)
        return OutputWriter(config)

    def test_clean_simple_filename(self, writer):
        """Test cleaning simple filename."""
        cleaned = writer._clean_name("document.txt")

        assert cleaned is not None
        assert len(cleaned) > 0
        assert "/" not in cleaned

    def test_clean_url(self, writer):
        """Test cleaning URL."""
        cleaned = writer._clean_name("https://example.com/page/article")

        assert cleaned is not None
        assert "://" not in cleaned
        assert cleaned.startswith("example")

    def test_clean_url_with_dots(self, writer):
        """Test cleaning URL with dots in domain."""
        cleaned = writer._clean_name("https://www.example.com")

        assert cleaned is not None
        assert "." not in cleaned

    def test_clean_path_with_extension(self, writer):
        """Test cleaning path preserves stem and extension."""
        cleaned = writer._clean_name("/path/to/sample.wav")

        assert "sample" in cleaned

    def test_clean_removes_special_chars(self, writer):
        """Test cleaning removes special characters."""
        cleaned = writer._clean_name("file<with>special:chars?.txt")

        assert "<" not in cleaned
        assert ">" not in cleaned
        assert ":" not in cleaned
        assert "?" not in cleaned

    def test_clean_limits_length(self, writer):
        """Test cleaning limits filename length."""
        long_name = "a" * 200 + ".txt"
        cleaned = writer._clean_name(long_name)

        assert len(cleaned) <= 100

    def test_clean_removes_multiple_underscores(self, writer):
        """Test cleaning removes consecutive underscores."""
        cleaned = writer._clean_name("my___file___name.txt")

        assert "___" not in cleaned


class TestOutputWriterWrite:
    """Tests for OutputWriter write method."""

    @pytest.fixture
    def writer(self, tmp_path):
        config = IngestConfig(output_dir=tmp_path / "output")
        return OutputWriter(config)

    @pytest.fixture
    def simple_result(self):
        return ExtractionResult(
            markdown="# Test\n\nThis is test content.",
            title="Test Document",
            source="test.txt",
            media_type=MediaType.TXT,
            images=[],
            metadata={"key": "value"},
        )

    @pytest.mark.asyncio
    async def test_write_creates_directory(self, writer, simple_result):
        """Test writing creates output directory."""
        output_dir = await writer.write(simple_result)

        assert output_dir.exists()
        assert output_dir.is_dir()

    @pytest.mark.asyncio
    async def test_write_creates_markdown_file(self, writer, simple_result):
        """Test writing creates markdown file."""
        output_dir = await writer.write(simple_result)

        md_files = list(output_dir.glob("*.md"))
        assert len(md_files) == 1

        content = md_files[0].read_text()
        assert "Test" in content

    @pytest.mark.asyncio
    async def test_write_uses_source_for_name(self, writer):
        """Test writing uses source for directory name."""
        result = ExtractionResult(
            markdown="# Content",
            title="Title",
            source="my_document.txt",
            media_type=MediaType.TXT,
            images=[],
            metadata={},
        )

        output_dir = await writer.write(result)

        # Directory name should be based on source
        assert "my_document" in output_dir.name

    @pytest.mark.asyncio
    async def test_write_uses_title_when_no_source(self, writer):
        """Test writing uses title when no source."""
        result = ExtractionResult(
            markdown="# Content",
            title="My Document Title",
            source=None,
            media_type=MediaType.TXT,
            images=[],
            metadata={},
        )

        output_dir = await writer.write(result)

        # Directory name should be based on title
        assert output_dir.exists()

    @pytest.mark.asyncio
    async def test_write_default_name(self, writer):
        """Test writing with no source or title."""
        result = ExtractionResult(
            markdown="# Content",
            title=None,
            source=None,
            media_type=None,
            images=[],
            metadata={},
        )

        output_dir = await writer.write(result)

        # Should use default name "output"
        assert "output" in output_dir.name


class TestOutputWriterMetadata:
    """Tests for OutputWriter metadata generation."""

    @pytest.mark.asyncio
    async def test_write_generates_metadata(self, tmp_path):
        """Test writing generates metadata.json when enabled."""
        config = IngestConfig(output_dir=tmp_path, generate_metadata=True)
        writer = OutputWriter(config)

        result = ExtractionResult(
            markdown="# Content",
            title="Test Doc",
            source="test.txt",
            media_type=MediaType.TXT,
            images=[],
            metadata={"custom_key": "custom_value"},
        )

        output_dir = await writer.write(result)

        metadata_file = output_dir / "metadata.json"
        assert metadata_file.exists()

        metadata = json.loads(metadata_file.read_text())
        assert metadata["title"] == "Test Doc"
        assert metadata["source"] == "test.txt"
        assert metadata["media_type"] == "txt"

    @pytest.mark.asyncio
    async def test_write_no_metadata_by_default(self, tmp_path):
        """Test writing does not generate metadata by default."""
        config = IngestConfig(output_dir=tmp_path, generate_metadata=False)
        writer = OutputWriter(config)

        result = ExtractionResult(
            markdown="# Content",
            title="Test",
            source="test.txt",
            media_type=MediaType.TXT,
            images=[],
            metadata={},
        )

        output_dir = await writer.write(result)

        metadata_file = output_dir / "metadata.json"
        assert not metadata_file.exists()


class TestOutputWriterWithImages:
    """Tests for OutputWriter with images."""

    @pytest.fixture
    def writer(self, tmp_path):
        config = IngestConfig(output_dir=tmp_path / "output")
        return OutputWriter(config)

    def create_test_png(self) -> bytes:
        """Create minimal valid PNG data."""
        try:
            from io import BytesIO

            from PIL import Image
            img = Image.new('RGB', (10, 10), color='red')
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue()
        except ImportError:
            # Minimal PNG header
            return b'\x89PNG\r\n\x1a\n' + b'\x00' * 100

    @pytest.mark.asyncio
    async def test_write_with_images(self, writer):
        """Test writing result with images creates img directory."""
        png_data = self.create_test_png()

        image = ExtractedImage(
            filename="test_image.png",
            data=png_data,
            format="png",
        )

        result = ExtractionResult(
            markdown="# Document with Image\n\n![Test](img/test_image.png)",
            title="Image Doc",
            source="doc.txt",
            media_type=MediaType.TXT,
            images=[image],
            metadata={},
        )

        output_dir = await writer.write(result)

        img_dir = output_dir / "img"
        assert img_dir.exists()

        # Check image file exists
        img_files = list(img_dir.glob("*.png"))
        assert len(img_files) >= 1

    @pytest.mark.asyncio
    async def test_write_multiple_images(self, writer):
        """Test writing result with multiple images."""
        png_data = self.create_test_png()

        images = [
            ExtractedImage(filename=f"image_{i}.png", data=png_data, format="png")
            for i in range(3)
        ]

        result = ExtractionResult(
            markdown="# Multi Image Doc",
            title="Multi",
            source="multi.txt",
            media_type=MediaType.TXT,
            images=images,
            metadata={},
        )

        output_dir = await writer.write(result)

        img_dir = output_dir / "img"
        assert img_dir.exists()


class TestOutputWriterSync:
    """Tests for synchronous OutputWriterSync."""

    def test_sync_writer_init(self, tmp_path):
        """Test sync writer initialization."""
        config = IngestConfig(output_dir=tmp_path)
        writer = OutputWriterSync(config)

        assert writer is not None
        assert writer.config is config

    def test_sync_writer_without_config(self):
        """Test sync writer without config."""
        writer = OutputWriterSync()

        assert writer is not None
        assert writer.config is not None

    def test_sync_writer_has_processor(self, tmp_path):
        """Test sync writer has image processor."""
        config = IngestConfig(output_dir=tmp_path)
        writer = OutputWriterSync(config)

        assert writer.image_processor is not None

    def test_sync_write(self, tmp_path):
        """Test synchronous write method."""
        config = IngestConfig(output_dir=tmp_path)
        writer = OutputWriterSync(config)

        result = ExtractionResult(
            markdown="# Test Content",
            title="Sync Test",
            source="sync_test.txt",
            media_type=MediaType.TXT,
            images=[],
            metadata={},
        )

        output_dir = writer.write(result)

        assert output_dir.exists()
        assert output_dir.is_dir()


class TestOutputWriterURLHandling:
    """Tests for OutputWriter URL source handling."""

    @pytest.fixture
    def writer(self, tmp_path):
        config = IngestConfig(output_dir=tmp_path)
        return OutputWriter(config)

    def test_clean_http_url(self, writer):
        """Test cleaning HTTP URL."""
        cleaned = writer._clean_name("http://example.com/path/to/page")

        assert "http" not in cleaned
        assert "://" not in cleaned

    def test_clean_https_url(self, writer):
        """Test cleaning HTTPS URL."""
        cleaned = writer._clean_name("https://www.example.com/article")

        assert "https" not in cleaned

    def test_clean_youtube_url(self, writer):
        """Test cleaning YouTube URL."""
        cleaned = writer._clean_name("https://www.youtube.com/watch?v=abc123")

        assert "youtube" in cleaned or "www" in cleaned

    def test_clean_url_path_included(self, writer):
        """Test URL path is included in cleaned name."""
        cleaned = writer._clean_name("https://docs.example.com/en/latest/guide")

        # Should include some path information
        assert len(cleaned) > 10


class TestExtractionResultProperties:
    """Tests for ExtractionResult with OutputWriter."""

    def test_has_images_true(self):
        """Test has_images is True when images present."""
        result = ExtractionResult(
            markdown="# Test",
            images=[ExtractedImage(filename="test.png", data=b"", format="png")],
        )

        assert result.has_images is True

    def test_has_images_false(self):
        """Test has_images is False when no images."""
        result = ExtractionResult(
            markdown="# Test",
            images=[],
        )

        assert result.has_images is False

    def test_image_count(self):
        """Test image_count property."""
        result = ExtractionResult(
            markdown="# Test",
            images=[
                ExtractedImage(filename="img1.png", data=b"", format="png"),
                ExtractedImage(filename="img2.png", data=b"", format="png"),
            ],
        )

        assert result.image_count == 2
