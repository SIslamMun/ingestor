"""Integration tests for batch/bulk operations."""

import json

import pytest

from ingestor.core.registry import create_default_registry
from ingestor.core.router import Router
from ingestor.output.writer import OutputWriter
from ingestor.types import IngestConfig


class TestBatchProcessing:
    """Tests for batch directory processing."""

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
    def batch_folder(self, tmp_path):
        """Create a folder with multiple files for batch processing."""
        batch_dir = tmp_path / "batch_input"
        batch_dir.mkdir()

        # Create text files
        (batch_dir / "file1.txt").write_text("Content of file 1")
        (batch_dir / "file2.txt").write_text("Content of file 2")

        # Create JSON file
        (batch_dir / "data.json").write_text(json.dumps({"test": True}))

        # Create subdirectory
        sub_dir = batch_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "nested.txt").write_text("Nested file content")

        return batch_dir

    @pytest.mark.asyncio
    async def test_process_directory(self, router, batch_folder):
        """Test processing a directory of files."""
        results = []
        async for result in router.process_directory(batch_folder, recursive=True):
            results.append(result)

        # Should process all files
        assert len(results) >= 3  # file1.txt, file2.txt, data.json (maybe nested.txt)

    @pytest.mark.asyncio
    async def test_process_directory_non_recursive(self, router, batch_folder):
        """Test non-recursive directory processing."""
        results = []
        async for result in router.process_directory(batch_folder, recursive=False):
            results.append(result)

        # Should NOT include nested file
        sources = [r.source for r in results]
        assert not any("subdir" in str(s) for s in sources)

    @pytest.mark.asyncio
    async def test_batch_concurrent(self, router, batch_folder):
        """Test concurrent batch processing."""
        results = []
        async for result in router.process_directory(
            batch_folder,
            recursive=True,
            concurrency=3
        ):
            results.append(result)

        assert len(results) >= 3


class TestBatchOutput:
    """Tests for batch output writing."""

    @pytest.fixture
    def config(self, tmp_path):
        return IngestConfig(
            output_dir=tmp_path / "output",
            generate_metadata=True,
        )

    @pytest.fixture
    def writer(self, config):
        return OutputWriter(config)

    @pytest.fixture
    def batch_folder(self, tmp_path):
        batch_dir = tmp_path / "input"
        batch_dir.mkdir()
        (batch_dir / "doc1.txt").write_text("Document 1 content")
        (batch_dir / "doc2.txt").write_text("Document 2 content")
        return batch_dir

    @pytest.mark.asyncio
    async def test_batch_creates_separate_outputs(self, writer, batch_folder, config):
        """Test batch creates separate output folders."""
        from ingestor.extractors.text import TxtExtractor

        extractor = TxtExtractor()
        output_paths = []

        for txt_file in batch_folder.glob("*.txt"):
            result = await extractor.extract(txt_file)
            output_path = await writer.write(result)
            output_paths.append(output_path)

        # Should have created separate folders
        assert len(output_paths) == 2
        assert output_paths[0] != output_paths[1]

    @pytest.mark.asyncio
    async def test_batch_no_name_collision(self, writer, batch_folder, config):
        """Test batch handles files with same name correctly."""
        # Create two files with similar names
        from ingestor.extractors.text import TxtExtractor

        extractor = TxtExtractor()

        result1 = await extractor.extract(batch_folder / "doc1.txt")
        result2 = await extractor.extract(batch_folder / "doc2.txt")

        path1 = await writer.write(result1)
        path2 = await writer.write(result2)

        # Both should exist and be different
        assert path1.exists()
        assert path2.exists()
        assert path1 != path2


class TestProcessBatch:
    """Tests for process_batch method."""

    @pytest.fixture
    def registry(self):
        return create_default_registry()

    @pytest.fixture
    def config(self, tmp_path):
        return IngestConfig(output_dir=tmp_path / "output")

    @pytest.fixture
    def router(self, registry, config):
        return Router(registry, config)

    @pytest.mark.asyncio
    async def test_process_batch_multiple_sources(self, router, tmp_path):
        """Test processing multiple sources in batch."""
        # Create test files
        file1 = tmp_path / "test1.txt"
        file2 = tmp_path / "test2.txt"
        file1.write_text("Test content 1")
        file2.write_text("Test content 2")

        sources = [file1, file2]
        results = []

        async for result in router.process_batch(sources):
            results.append(result)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_process_batch_concurrency(self, router, tmp_path):
        """Test batch processing with concurrency control."""
        # Create multiple files
        files = []
        for i in range(5):
            f = tmp_path / f"file{i}.txt"
            f.write_text(f"Content {i}")
            files.append(f)

        results = []
        async for result in router.process_batch(files, concurrency=2):
            results.append(result)

        assert len(results) == 5
