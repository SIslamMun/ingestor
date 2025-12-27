"""Integration tests for the full extraction pipeline."""


import pytest

from ingestor.core.registry import create_default_registry
from ingestor.core.router import Router
from ingestor.output.writer import OutputWriter
from ingestor.types import IngestConfig, MediaType


class TestFullPipeline:
    """Tests for the complete extraction pipeline."""

    @pytest.fixture
    def registry(self):
        return create_default_registry()

    @pytest.fixture
    def config(self, tmp_path):
        return IngestConfig(
            output_dir=tmp_path / "output",
            keep_raw_images=False,
            target_image_format="png",
            generate_metadata=True,
        )

    @pytest.fixture
    def router(self, registry, config):
        return Router(registry, config)

    @pytest.fixture
    def writer(self, config):
        return OutputWriter(config)

    @pytest.mark.asyncio
    async def test_text_file_pipeline(self, router, writer, sample_txt, config):
        """Test full pipeline for text file."""
        if not sample_txt.exists():
            pytest.skip("Fixture not generated")

        # Process
        result = await router.process(sample_txt)

        # Write
        output_path = await writer.write(result)

        # Verify
        assert output_path.exists()
        md_files = list(output_path.glob("*.md"))
        assert len(md_files) >= 1

    @pytest.mark.asyncio
    async def test_json_file_pipeline(self, router, writer, sample_json, config):
        """Test full pipeline for JSON file."""
        if not sample_json.exists():
            pytest.skip("Fixture not generated")

        result = await router.process(sample_json)
        output_path = await writer.write(result)

        assert output_path.exists()
        # Should have markdown output
        md_content = list(output_path.glob("*.md"))[0].read_text()
        assert len(md_content) > 0

    @pytest.mark.asyncio
    async def test_metadata_generation(self, router, writer, sample_txt, config):
        """Test metadata JSON generation."""
        if not sample_txt.exists():
            pytest.skip("Fixture not generated")

        result = await router.process(sample_txt)
        output_path = await writer.write(result)

        # Should have metadata.json
        metadata_file = output_path / "metadata.json"
        assert metadata_file.exists()

    def test_can_process(self, router, sample_txt):
        """Test can_process check."""
        if not sample_txt.exists():
            pytest.skip("Fixture not generated")

        assert router.can_process(sample_txt)
        assert router.can_process(str(sample_txt))

    def test_detect_type(self, router, sample_txt, sample_json):
        """Test type detection."""
        if not sample_txt.exists():
            pytest.skip("Fixture not generated")

        assert router.detect_type(sample_txt) == MediaType.TXT

        if sample_json.exists():
            assert router.detect_type(sample_json) == MediaType.JSON


class TestOutputStructure:
    """Tests for output directory structure."""

    @pytest.fixture
    def config(self, tmp_path):
        return IngestConfig(
            output_dir=tmp_path / "output",
            keep_raw_images=False,
            target_image_format="png",
            generate_metadata=True,
        )

    @pytest.fixture
    def writer(self, config):
        return OutputWriter(config)

    @pytest.mark.asyncio
    async def test_creates_output_dir(self, writer, sample_txt, config):
        """Test output directory is created."""
        if not sample_txt.exists():
            pytest.skip("Fixture not generated")

        from ingestor.extractors.text import TxtExtractor

        extractor = TxtExtractor()
        result = await extractor.extract(sample_txt)
        output_path = await writer.write(result)

        assert output_path.exists()
        assert output_path.is_dir()

    @pytest.mark.asyncio
    async def test_creates_img_folder_when_images(self, writer, sample_png, config):
        """Test img folder is created when images exist."""
        if not sample_png.exists():
            pytest.skip("Fixture not generated")

        from ingestor.extractors.image import ImageExtractor

        extractor = ImageExtractor()
        result = await extractor.extract(sample_png)
        output_path = await writer.write(result)

        img_folder = output_path / "img"
        # Should exist if images were extracted
        if result.images:
            assert img_folder.exists()
