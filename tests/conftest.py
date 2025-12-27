"""Pytest configuration and shared fixtures."""

from pathlib import Path

import pytest

from ingestor.core.registry import ExtractorRegistry, create_default_registry
from ingestor.types import IngestConfig

# ============================================================================
# Path Fixtures
# ============================================================================

@pytest.fixture
def fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def documents_dir(fixtures_dir: Path) -> Path:
    """Path to document fixtures."""
    return fixtures_dir / "documents"


@pytest.fixture
def spreadsheets_dir(fixtures_dir: Path) -> Path:
    """Path to spreadsheet fixtures."""
    return fixtures_dir / "spreadsheets"


@pytest.fixture
def data_dir(fixtures_dir: Path) -> Path:
    """Path to data format fixtures."""
    return fixtures_dir / "data"


@pytest.fixture
def images_dir(fixtures_dir: Path) -> Path:
    """Path to image fixtures."""
    return fixtures_dir / "images"


@pytest.fixture
def archives_dir(fixtures_dir: Path) -> Path:
    """Path to archive fixtures."""
    return fixtures_dir / "archives"


@pytest.fixture
def audio_dir(fixtures_dir: Path) -> Path:
    """Path to audio fixtures."""
    return fixtures_dir / "audio"


@pytest.fixture
def ebooks_dir(fixtures_dir: Path) -> Path:
    """Path to ebook fixtures."""
    return fixtures_dir / "ebooks"


# ============================================================================
# Sample File Fixtures
# ============================================================================

@pytest.fixture
def sample_txt(documents_dir: Path) -> Path:
    """Sample UTF-8 text file."""
    return documents_dir / "sample.txt"


@pytest.fixture
def sample_md(documents_dir: Path) -> Path:
    """Sample Markdown file."""
    return documents_dir / "sample.md"


@pytest.fixture
def sample_rst(documents_dir: Path) -> Path:
    """Sample reStructuredText file."""
    return documents_dir / "sample.rst"


@pytest.fixture
def sample_txt_latin1(documents_dir: Path) -> Path:
    """Sample Latin-1 encoded text file."""
    return documents_dir / "sample_latin1.txt"


@pytest.fixture
def sample_json(data_dir: Path) -> Path:
    """Sample JSON file."""
    return data_dir / "sample.json"


@pytest.fixture
def sample_json_array(data_dir: Path) -> Path:
    """Sample JSON array file (tabular)."""
    return data_dir / "sample_array.json"


@pytest.fixture
def sample_xml(data_dir: Path) -> Path:
    """Sample XML file."""
    return data_dir / "sample.xml"


@pytest.fixture
def sample_csv(spreadsheets_dir: Path) -> Path:
    """Sample CSV file."""
    return spreadsheets_dir / "sample.csv"


@pytest.fixture
def sample_xlsx(spreadsheets_dir: Path) -> Path:
    """Sample XLSX file."""
    return spreadsheets_dir / "sample.xlsx"


@pytest.fixture
def sample_png(images_dir: Path) -> Path:
    """Sample PNG image."""
    return images_dir / "sample.png"


@pytest.fixture
def sample_jpg(images_dir: Path) -> Path:
    """Sample JPEG image."""
    return images_dir / "sample.jpg"


@pytest.fixture
def sample_docx(documents_dir: Path) -> Path:
    """Sample DOCX file."""
    return documents_dir / "sample.docx"


@pytest.fixture
def sample_pptx(documents_dir: Path) -> Path:
    """Sample PPTX file."""
    return documents_dir / "sample.pptx"


@pytest.fixture
def sample_zip(archives_dir: Path) -> Path:
    """Sample ZIP archive."""
    return archives_dir / "sample.zip"


@pytest.fixture
def sample_wav(audio_dir: Path) -> Path:
    """Sample WAV audio file."""
    return audio_dir / "sample.wav"


@pytest.fixture
def sample_epub(ebooks_dir: Path) -> Path:
    """Sample EPUB ebook file."""
    return ebooks_dir / "sample.epub"


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def temp_output(tmp_path: Path) -> Path:
    """Temporary output directory."""
    output = tmp_path / "output"
    output.mkdir()
    return output


@pytest.fixture
def config(temp_output: Path) -> IngestConfig:
    """Default test configuration."""
    return IngestConfig(
        output_dir=temp_output,
        keep_raw_images=False,
        target_image_format="png",
        generate_metadata=True,
        verbose=False,
    )


@pytest.fixture
def config_keep_raw(temp_output: Path) -> IngestConfig:
    """Configuration that keeps raw images."""
    return IngestConfig(
        output_dir=temp_output,
        keep_raw_images=True,
        target_image_format="png",
        generate_metadata=False,
        verbose=False,
    )


# ============================================================================
# Registry Fixtures
# ============================================================================

@pytest.fixture
def registry() -> ExtractorRegistry:
    """Fully populated extractor registry."""
    return create_default_registry()


@pytest.fixture
def empty_registry() -> ExtractorRegistry:
    """Empty extractor registry for testing registration."""
    return ExtractorRegistry()


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--network",
        action="store_true",
        default=False,
        help="Run tests that require network access",
    )


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "network: marks tests as requiring network access"
    )
    config.addinivalue_line(
        "markers", "skip_audio: marks tests to skip for audio (slow)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Skip network tests unless --network is passed."""
    if not config.getoption("--network"):
        skip_network = pytest.mark.skip(reason="need --network option to run")
        for item in items:
            if "network" in item.keywords:
                item.add_marker(skip_network)


# ============================================================================
# Helper Fixtures
# ============================================================================

@pytest.fixture
def known_text_content() -> str:
    """Known text content for comparison."""
    return """# Test Document

This is a test document with known content.

## Section 1

Some text in section 1.

## Section 2

Some text in section 2.
"""


@pytest.fixture
def known_json_content() -> dict:
    """Known JSON content for comparison."""
    return {
        "title": "Test Document",
        "version": 1,
        "items": [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
        ],
    }


@pytest.fixture
def known_csv_content() -> str:
    """Known CSV content for comparison."""
    return """name,age,city
Alice,30,New York
Bob,25,San Francisco
Charlie,35,Chicago
"""
