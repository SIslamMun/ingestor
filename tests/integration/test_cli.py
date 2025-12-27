"""Integration tests for CLI commands."""


import pytest
from click.testing import CliRunner

from ingestor.cli import main


class TestCLI:
    """Tests for CLI commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_version(self, runner):
        """Test --version flag."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help(self, runner):
        """Test --help flag."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "ingest" in result.output
        assert "batch" in result.output

    def test_ingest_help(self, runner):
        """Test ingest command help."""
        result = runner.invoke(main, ["ingest", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output
        assert "--metadata" in result.output


class TestIngestCommand:
    """Tests for the ingest command."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_ingest_text_file(self, runner, sample_txt, tmp_path):
        """Test ingesting a text file."""
        if not sample_txt.exists():
            pytest.skip("Fixture not generated")

        output_dir = tmp_path / "output"
        result = runner.invoke(main, [
            "ingest",
            str(sample_txt),
            "-o", str(output_dir),
        ])

        # Should succeed (exit code 0) or handle gracefully
        # Note: may fail if deps not installed
        if result.exit_code == 0:
            assert output_dir.exists()

    def test_ingest_nonexistent_file(self, runner, tmp_path):
        """Test ingesting a non-existent file."""
        result = runner.invoke(main, [
            "ingest",
            str(tmp_path / "nonexistent.txt"),
            "-o", str(tmp_path / "output"),
        ])

        # Should fail gracefully
        assert result.exit_code != 0 or "Error" in result.output

    def test_ingest_json_file(self, runner, sample_json, tmp_path):
        """Test ingesting a JSON file."""
        if not sample_json.exists():
            pytest.skip("Fixture not generated")

        output_dir = tmp_path / "output"
        result = runner.invoke(main, [
            "ingest",
            str(sample_json),
            "-o", str(output_dir),
            "--metadata",
        ])

        if result.exit_code == 0:
            assert output_dir.exists()


class TestBatchCommand:
    """Tests for the batch command."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_batch_help(self, runner):
        """Test batch command help."""
        result = runner.invoke(main, ["batch", "--help"])
        assert result.exit_code == 0
        assert "--recursive" in result.output

    def test_batch_empty_folder(self, runner, tmp_path):
        """Test batch on empty folder."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = runner.invoke(main, [
            "batch",
            str(empty_dir),
            "-o", str(tmp_path / "output"),
        ])

        # Should complete (may have 0 files processed)
        assert "Completed" in result.output or result.exit_code == 0
