"""Reference tests for exact output comparison.

These tests compare extractor output against known reference files.
Any difference indicates a potential regression.
"""

import pytest
from pathlib import Path
from typing import Optional
import difflib

from ingestor.extractors.text.txt_extractor import TxtExtractor
from ingestor.extractors.data.json_extractor import JsonExtractor
from ingestor.extractors.data.csv_extractor import CsvExtractor


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def reference_dir() -> Path:
    """Path to reference fixtures directory."""
    return Path(__file__).parent.parent / "fixtures" / "reference"


@pytest.fixture
def txt_extractor():
    """Text extractor instance."""
    return TxtExtractor()


@pytest.fixture
def json_extractor():
    """JSON extractor instance."""
    return JsonExtractor()


@pytest.fixture
def csv_extractor():
    """CSV extractor instance."""
    return CsvExtractor()


# ============================================================================
# Helper Functions
# ============================================================================

def normalize_markdown(text: str) -> str:
    """Normalize markdown for comparison.
    
    - Strip trailing whitespace from lines
    - Normalize line endings
    - Strip leading/trailing whitespace from whole text
    """
    lines = text.replace('\r\n', '\n').split('\n')
    lines = [line.rstrip() for line in lines]
    return '\n'.join(lines).strip()


def compare_markdown(actual: str, expected: str) -> tuple[bool, str]:
    """Compare two markdown strings and return diff if different.
    
    Returns:
        (match, diff_output) - True if match, otherwise diff string
    """
    actual_norm = normalize_markdown(actual)
    expected_norm = normalize_markdown(expected)
    
    if actual_norm == expected_norm:
        return True, ""
    
    # Generate unified diff
    actual_lines = actual_norm.split('\n')
    expected_lines = expected_norm.split('\n')
    
    diff = difflib.unified_diff(
        expected_lines,
        actual_lines,
        fromfile='expected',
        tofile='actual',
        lineterm=''
    )
    
    return False, '\n'.join(diff)


def load_reference(reference_dir: Path, input_name: str) -> tuple[Optional[Path], Optional[str]]:
    """Load a reference input file and its expected output.
    
    Args:
        reference_dir: Directory containing reference files
        input_name: Name of input file (e.g., "simple.md")
    
    Returns:
        (input_path, expected_content) or (None, None) if not found
    """
    input_path = reference_dir / input_name
    expected_path = reference_dir / f"{input_name}.expected.md"
    
    if not input_path.exists():
        return None, None
    
    if not expected_path.exists():
        return input_path, None
    
    expected_content = expected_path.read_text(encoding='utf-8')
    return input_path, expected_content


# ============================================================================
# Text Reference Tests
# ============================================================================

class TestTextReferences:
    """Reference tests for text file extraction."""
    
    @pytest.mark.asyncio
    async def test_simple_md_reference(self, reference_dir, txt_extractor):
        """Test simple markdown extraction matches reference."""
        input_path, expected = load_reference(reference_dir, "simple.md")
        
        if input_path is None:
            pytest.skip("Reference file simple.md not found")
        
        result = await txt_extractor.extract(input_path)
        
        if expected is not None:
            match, diff = compare_markdown(result.markdown, expected)
            assert match, f"Output doesn't match reference:\n{diff}"
    
    @pytest.mark.asyncio
    async def test_empty_file_reference(self, reference_dir, txt_extractor):
        """Test empty file extraction."""
        input_path, expected = load_reference(reference_dir, "empty.txt")
        
        if input_path is None:
            pytest.skip("Reference file empty.txt not found")
        
        result = await txt_extractor.extract(input_path)
        
        # Empty file should produce empty or minimal output
        assert len(result.markdown.strip()) == 0 or result.markdown.strip() == ""
    
    @pytest.mark.asyncio
    async def test_whitespace_only_reference(self, reference_dir, txt_extractor):
        """Test whitespace-only file extraction."""
        input_path, expected = load_reference(reference_dir, "whitespace_only.txt")
        
        if input_path is None:
            pytest.skip("Reference file whitespace_only.txt not found")
        
        result = await txt_extractor.extract(input_path)
        
        # Whitespace-only should produce empty output
        assert len(result.markdown.strip()) == 0
    
    @pytest.mark.asyncio
    async def test_unicode_content_reference(self, reference_dir, txt_extractor):
        """Test unicode content extraction."""
        input_path, expected = load_reference(reference_dir, "unicode_content.txt")
        
        if input_path is None:
            pytest.skip("Reference file unicode_content.txt not found")
        
        result = await txt_extractor.extract(input_path)
        
        # Check unicode characters are preserved
        assert "こんにちは" in result.markdown
        assert "مرحبا" in result.markdown
        assert "Привет" in result.markdown
        assert "🎉" in result.markdown
    
    @pytest.mark.asyncio
    async def test_special_chars_reference(self, reference_dir, txt_extractor):
        """Test special characters extraction."""
        input_path, expected = load_reference(reference_dir, "special_chars.txt")
        
        if input_path is None:
            pytest.skip("Reference file special_chars.txt not found")
        
        result = await txt_extractor.extract(input_path)
        
        if expected is not None:
            match, diff = compare_markdown(result.markdown, expected)
            assert match, f"Output doesn't match reference:\n{diff}"
    
    @pytest.mark.asyncio
    async def test_long_line_reference(self, reference_dir, txt_extractor):
        """Test long line handling."""
        input_path, expected = load_reference(reference_dir, "long_line.txt")
        
        if input_path is None:
            pytest.skip("Reference file long_line.txt not found")
        
        result = await txt_extractor.extract(input_path)
        
        # Should preserve long lines
        assert "A" * 100 in result.markdown  # At least 100 A's


# ============================================================================
# JSON Reference Tests
# ============================================================================

class TestJsonReferences:
    """Reference tests for JSON file extraction."""
    
    @pytest.mark.asyncio
    async def test_edge_cases_json(self, reference_dir, json_extractor):
        """Test JSON edge cases extraction."""
        input_path, expected = load_reference(reference_dir, "edge_cases.json")
        
        if input_path is None:
            pytest.skip("Reference file edge_cases.json not found")
        
        result = await json_extractor.extract(input_path)
        
        # Check key content is preserved
        assert "null" in result.markdown.lower() or "None" in result.markdown
        assert "日本語テスト" in result.markdown
        assert "42" in result.markdown
        assert "3.14159" in result.markdown


# ============================================================================
# CSV Reference Tests
# ============================================================================

class TestCsvReferences:
    """Reference tests for CSV file extraction."""
    
    @pytest.mark.asyncio
    async def test_edge_cases_csv(self, reference_dir, csv_extractor):
        """Test CSV edge cases extraction."""
        input_path, expected = load_reference(reference_dir, "edge_cases.csv")
        
        if input_path is None:
            pytest.skip("Reference file edge_cases.csv not found")
        
        result = await csv_extractor.extract(input_path)
        
        # Check table structure exists
        assert "|" in result.markdown  # Table format
        assert "Simple" in result.markdown
        assert "With, Comma" in result.markdown or "With Comma" in result.markdown


# ============================================================================
# Document Reference Tests (require optional dependencies)
# ============================================================================

class TestDocxReferences:
    """Reference tests for DOCX extraction."""
    
    @pytest.fixture
    def docx_extractor(self):
        """DOCX extractor instance."""
        try:
            from ingestor.extractors.docx.docx_extractor import DocxExtractor
            return DocxExtractor()
        except ImportError:
            pytest.skip("python-docx not installed")
    
    @pytest.mark.asyncio
    async def test_complex_docx_reference(self, reference_dir, docx_extractor):
        """Test complex DOCX extraction."""
        input_path, expected = load_reference(reference_dir, "complex.docx")
        
        if input_path is None:
            pytest.skip("Reference file complex.docx not found")
        
        result = await docx_extractor.extract(input_path)
        
        # Check key content is extracted
        assert "Complex Document Test" in result.markdown
        assert "Section 1" in result.markdown
        assert "Tables" in result.markdown
        assert "Alice" in result.markdown
        assert "Lists" in result.markdown


class TestXlsxReferences:
    """Reference tests for XLSX extraction."""
    
    @pytest.fixture
    def xlsx_extractor(self):
        """XLSX extractor instance."""
        try:
            from ingestor.extractors.excel.xlsx_extractor import XlsxExtractor
            return XlsxExtractor()
        except ImportError:
            pytest.skip("openpyxl not installed")
    
    @pytest.mark.asyncio
    async def test_complex_xlsx_reference(self, reference_dir, xlsx_extractor):
        """Test complex XLSX extraction."""
        input_path, expected = load_reference(reference_dir, "complex.xlsx")
        
        if input_path is None:
            pytest.skip("Reference file complex.xlsx not found")
        
        result = await xlsx_extractor.extract(input_path)
        
        # Check key content is extracted
        assert "Sales" in result.markdown or "Product" in result.markdown
        assert "Widget" in result.markdown
        assert "|" in result.markdown  # Table format


class TestPptxReferences:
    """Reference tests for PPTX extraction."""
    
    @pytest.fixture
    def pptx_extractor(self):
        """PPTX extractor instance."""
        try:
            from ingestor.extractors.pptx.pptx_extractor import PptxExtractor
            return PptxExtractor()
        except ImportError:
            pytest.skip("python-pptx not installed")
    
    @pytest.mark.asyncio
    async def test_complex_pptx_reference(self, reference_dir, pptx_extractor):
        """Test complex PPTX extraction."""
        input_path, expected = load_reference(reference_dir, "complex.pptx")
        
        if input_path is None:
            pytest.skip("Reference file complex.pptx not found")
        
        result = await pptx_extractor.extract(input_path)
        
        # Check key content is extracted
        assert "Complex Presentation Test" in result.markdown
        assert "Bullet" in result.markdown
        assert "Table" in result.markdown or "Data" in result.markdown
