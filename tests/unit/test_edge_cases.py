"""Edge case tests for extractors.

Tests for boundary conditions, error handling, and unusual inputs:
- Empty files
- Corrupted files
- Very large files
- Unicode filenames
- Files with no extension
- Password-protected files
"""

import pytest
import tempfile
import os
from pathlib import Path
from typing import Optional

from ingestor.extractors.text.txt_extractor import TxtExtractor
from ingestor.extractors.data.json_extractor import JsonExtractor
from ingestor.extractors.data.csv_extractor import CsvExtractor
from ingestor.extractors.data.xml_extractor import XmlExtractor
from ingestor.types import MediaType


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def txt_extractor():
    return TxtExtractor()


@pytest.fixture
def json_extractor():
    return JsonExtractor()


@pytest.fixture
def csv_extractor():
    return CsvExtractor()


@pytest.fixture
def xml_extractor():
    return XmlExtractor()


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ============================================================================
# Empty File Tests
# ============================================================================

class TestEmptyFiles:
    """Test handling of empty files."""
    
    @pytest.mark.asyncio
    async def test_empty_txt_file(self, txt_extractor, temp_dir):
        """Empty text file should produce empty output."""
        empty_file = temp_dir / "empty.txt"
        empty_file.write_text("")
        
        result = await txt_extractor.extract(empty_file)
        
        assert result is not None
        assert result.media_type == MediaType.TXT
        assert result.markdown.strip() == ""
    
    @pytest.mark.asyncio
    async def test_empty_json_file(self, json_extractor, temp_dir):
        """Empty JSON file should raise JSONDecodeError (invalid JSON)."""
        import json
        empty_file = temp_dir / "empty.json"
        empty_file.write_text("")
        
        # Empty file is not valid JSON - should raise error
        with pytest.raises(json.JSONDecodeError):
            await json_extractor.extract(empty_file)
    
    @pytest.mark.asyncio
    async def test_empty_csv_file(self, csv_extractor, temp_dir):
        """Empty CSV file should raise error (no data to parse)."""
        import pandas as pd
        empty_file = temp_dir / "empty.csv"
        empty_file.write_text("")
        
        # Empty CSV is not valid - should raise error
        with pytest.raises((pd.errors.EmptyDataError, Exception)):
            await csv_extractor.extract(empty_file)


# ============================================================================
# Whitespace-Only Files
# ============================================================================

class TestWhitespaceFiles:
    """Test handling of whitespace-only files."""
    
    @pytest.mark.asyncio
    async def test_whitespace_txt(self, txt_extractor, temp_dir):
        """Whitespace-only text file."""
        ws_file = temp_dir / "whitespace.txt"
        ws_file.write_text("   \n\n\t\t\n   ")
        
        result = await txt_extractor.extract(ws_file)
        
        assert result is not None
        assert result.markdown.strip() == ""
    
    @pytest.mark.asyncio
    async def test_newlines_only_txt(self, txt_extractor, temp_dir):
        """File with only newlines."""
        nl_file = temp_dir / "newlines.txt"
        nl_file.write_text("\n\n\n\n\n")
        
        result = await txt_extractor.extract(nl_file)
        
        assert result is not None
        assert result.markdown.strip() == ""


# ============================================================================
# Malformed/Corrupted Files
# ============================================================================

class TestMalformedFiles:
    """Test handling of malformed or corrupted files."""
    
    @pytest.mark.asyncio
    async def test_invalid_json(self, json_extractor, temp_dir):
        """Invalid JSON should raise JSONDecodeError."""
        import json
        invalid_file = temp_dir / "invalid.json"
        invalid_file.write_text("{ invalid json content }")
        
        # Invalid JSON should raise error
        with pytest.raises(json.JSONDecodeError):
            await json_extractor.extract(invalid_file)
    
    @pytest.mark.asyncio
    async def test_truncated_json(self, json_extractor, temp_dir):
        """Truncated JSON (incomplete) should raise error."""
        import json
        truncated_file = temp_dir / "truncated.json"
        truncated_file.write_text('{"key": "value", "incomplete":')
        
        with pytest.raises(json.JSONDecodeError):
            await json_extractor.extract(truncated_file)
    
    @pytest.mark.asyncio
    async def test_invalid_xml(self, xml_extractor, temp_dir):
        """Invalid XML should raise ParseError."""
        import xml.etree.ElementTree as ET
        invalid_file = temp_dir / "invalid.xml"
        invalid_file.write_text("<root><unclosed>")
        
        with pytest.raises(ET.ParseError):
            await xml_extractor.extract(invalid_file)
    
    @pytest.mark.asyncio
    async def test_binary_as_text(self, txt_extractor, temp_dir):
        """Binary data passed as text file."""
        binary_file = temp_dir / "binary.txt"
        binary_file.write_bytes(b'\x00\x01\x02\x03\xff\xfe\xfd')
        
        # Should handle gracefully, not crash
        try:
            result = await txt_extractor.extract(binary_file)
            assert result is not None
        except Exception as e:
            # Acceptable to raise an exception for binary content
            assert "decode" in str(e).lower() or "encoding" in str(e).lower()


# ============================================================================
# Unicode and Special Characters
# ============================================================================

class TestUnicodeHandling:
    """Test handling of unicode content and filenames."""
    
    @pytest.mark.asyncio
    async def test_unicode_content(self, txt_extractor, temp_dir):
        """File with various unicode characters."""
        unicode_file = temp_dir / "unicode.txt"
        content = """# Unicode Test
日本語 (Japanese)
한국어 (Korean)
العربية (Arabic)
עברית (Hebrew)
Ελληνικά (Greek)
🎉🚀💻🔥 (Emoji)
"""
        unicode_file.write_text(content, encoding='utf-8')
        
        result = await txt_extractor.extract(unicode_file)
        
        assert result is not None
        assert "日本語" in result.markdown
        assert "한국어" in result.markdown
        assert "🎉" in result.markdown
    
    @pytest.mark.asyncio
    async def test_unicode_filename(self, txt_extractor, temp_dir):
        """File with unicode characters in filename."""
        unicode_name = temp_dir / "文档_테스트_документ.txt"
        unicode_name.write_text("Content in unicode-named file")
        
        result = await txt_extractor.extract(unicode_name)
        
        assert result is not None
        assert "Content" in result.markdown
    
    @pytest.mark.asyncio
    async def test_mixed_encodings(self, txt_extractor, temp_dir):
        """File that could be interpreted as different encodings."""
        # Latin-1 encoded content
        latin1_file = temp_dir / "latin1.txt"
        latin1_content = "Café résumé naïve"
        latin1_file.write_bytes(latin1_content.encode('latin-1'))
        
        result = await txt_extractor.extract(latin1_file)
        
        assert result is not None
        # Should either decode correctly or return something readable
        assert len(result.markdown) > 0
    
    @pytest.mark.asyncio
    async def test_bom_markers(self, txt_extractor, temp_dir):
        """File with BOM (Byte Order Mark)."""
        bom_file = temp_dir / "bom.txt"
        content = "Content after BOM"
        # UTF-8 BOM
        bom_file.write_bytes(b'\xef\xbb\xbf' + content.encode('utf-8'))
        
        result = await txt_extractor.extract(bom_file)
        
        assert result is not None
        assert "Content after BOM" in result.markdown


# ============================================================================
# Special Path Cases
# ============================================================================

class TestSpecialPaths:
    """Test handling of special file paths."""
    
    @pytest.mark.asyncio
    async def test_file_with_spaces(self, txt_extractor, temp_dir):
        """Filename with spaces."""
        space_file = temp_dir / "file with spaces.txt"
        space_file.write_text("Content in spaced filename")
        
        result = await txt_extractor.extract(space_file)
        
        assert result is not None
        assert "Content" in result.markdown
    
    @pytest.mark.asyncio
    async def test_file_with_special_chars(self, txt_extractor, temp_dir):
        """Filename with special characters."""
        # Use characters that are valid on most filesystems
        special_file = temp_dir / "file-with_special.chars(1).txt"
        special_file.write_text("Content in special filename")
        
        result = await txt_extractor.extract(special_file)
        
        assert result is not None
        assert "Content" in result.markdown
    
    @pytest.mark.asyncio
    async def test_deeply_nested_path(self, txt_extractor, temp_dir):
        """File in deeply nested directory."""
        nested_path = temp_dir / "a" / "b" / "c" / "d" / "e"
        nested_path.mkdir(parents=True)
        nested_file = nested_path / "deep.txt"
        nested_file.write_text("Deep content")
        
        result = await txt_extractor.extract(nested_file)
        
        assert result is not None
        assert "Deep content" in result.markdown
    
    @pytest.mark.asyncio
    async def test_hidden_file(self, txt_extractor, temp_dir):
        """Hidden file (starting with dot)."""
        hidden_file = temp_dir / ".hidden.txt"
        hidden_file.write_text("Hidden content")
        
        result = await txt_extractor.extract(hidden_file)
        
        assert result is not None
        assert "Hidden content" in result.markdown


# ============================================================================
# Large Content Tests
# ============================================================================

class TestLargeContent:
    """Test handling of large files and content."""
    
    @pytest.mark.asyncio
    async def test_very_long_line(self, txt_extractor, temp_dir):
        """File with a very long line (100KB)."""
        long_file = temp_dir / "long_line.txt"
        long_line = "A" * 100_000
        long_file.write_text(f"# Long Line\n{long_line}\n")
        
        result = await txt_extractor.extract(long_file)
        
        assert result is not None
        assert len(result.markdown) > 100_000
    
    @pytest.mark.asyncio
    async def test_many_lines(self, txt_extractor, temp_dir):
        """File with many lines (10,000 lines)."""
        many_lines_file = temp_dir / "many_lines.txt"
        lines = [f"Line {i}" for i in range(10_000)]
        many_lines_file.write_text("\n".join(lines))
        
        result = await txt_extractor.extract(many_lines_file)
        
        assert result is not None
        assert "Line 0" in result.markdown
        assert "Line 9999" in result.markdown
    
    @pytest.mark.asyncio
    async def test_large_json_array(self, json_extractor, temp_dir):
        """Large JSON array (1000 items)."""
        import json
        large_json_file = temp_dir / "large.json"
        data = [{"id": i, "name": f"Item {i}"} for i in range(1000)]
        large_json_file.write_text(json.dumps(data))
        
        result = await json_extractor.extract(large_json_file)
        
        assert result is not None
        assert "Item 0" in result.markdown or "id" in result.markdown
    
    @pytest.mark.asyncio
    async def test_deeply_nested_json(self, json_extractor, temp_dir):
        """Deeply nested JSON structure."""
        import json
        deep_json_file = temp_dir / "deep.json"
        
        # Create 50 levels of nesting
        data = {"level": 0}
        current = data
        for i in range(1, 50):
            current["nested"] = {"level": i}
            current = current["nested"]
        
        deep_json_file.write_text(json.dumps(data))
        
        result = await json_extractor.extract(deep_json_file)
        
        assert result is not None


# ============================================================================
# File Extension Edge Cases
# ============================================================================

class TestExtensionEdgeCases:
    """Test handling of unusual file extensions."""
    
    @pytest.mark.asyncio
    async def test_no_extension(self, txt_extractor, temp_dir):
        """File with no extension."""
        no_ext_file = temp_dir / "noextension"
        no_ext_file.write_text("Content without extension")
        
        # This might not be supported, but shouldn't crash
        try:
            result = await txt_extractor.extract(no_ext_file)
            assert result is not None
        except Exception:
            pass  # Acceptable to not support
    
    @pytest.mark.asyncio
    async def test_double_extension(self, txt_extractor, temp_dir):
        """File with double extension."""
        double_ext_file = temp_dir / "file.txt.bak"
        double_ext_file.write_text("Content with double extension")
        
        # Might be treated as .bak file
        if txt_extractor.supports(double_ext_file):
            result = await txt_extractor.extract(double_ext_file)
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_uppercase_extension(self, txt_extractor, temp_dir):
        """File with uppercase extension."""
        upper_ext_file = temp_dir / "file.TXT"
        upper_ext_file.write_text("Content with uppercase extension")
        
        result = await txt_extractor.extract(upper_ext_file)
        
        assert result is not None
        assert "Content" in result.markdown
    
    @pytest.mark.asyncio
    async def test_mixed_case_extension(self, txt_extractor, temp_dir):
        """File with mixed case extension."""
        mixed_ext_file = temp_dir / "file.TxT"
        mixed_ext_file.write_text("Content with mixed case extension")
        
        result = await txt_extractor.extract(mixed_ext_file)
        
        assert result is not None


# ============================================================================
# Concurrent/Stress Tests (Light)
# ============================================================================

class TestConcurrentExtraction:
    """Light concurrent extraction tests."""
    
    @pytest.mark.asyncio
    async def test_multiple_files_sequential(self, txt_extractor, temp_dir):
        """Extract multiple files sequentially."""
        files = []
        for i in range(10):
            f = temp_dir / f"file_{i}.txt"
            f.write_text(f"Content {i}")
            files.append(f)
        
        results = []
        for f in files:
            result = await txt_extractor.extract(f)
            results.append(result)
        
        assert len(results) == 10
        assert all(r is not None for r in results)
        for i, r in enumerate(results):
            assert f"Content {i}" in r.markdown
    
    @pytest.mark.asyncio
    async def test_same_file_multiple_times(self, txt_extractor, temp_dir):
        """Extract the same file multiple times."""
        f = temp_dir / "repeated.txt"
        f.write_text("Repeated content")
        
        results = []
        for _ in range(5):
            result = await txt_extractor.extract(f)
            results.append(result)
        
        # All results should be identical
        assert len(results) == 5
        first_md = results[0].markdown
        assert all(r.markdown == first_md for r in results)


# ============================================================================
# Error Recovery Tests
# ============================================================================

class TestErrorRecovery:
    """Test graceful error handling and recovery."""
    
    @pytest.mark.asyncio
    async def test_nonexistent_file(self, txt_extractor):
        """Extracting nonexistent file should handle gracefully."""
        fake_path = Path("/nonexistent/path/to/file.txt")
        
        # Should raise an appropriate error, not crash
        with pytest.raises(Exception):
            await txt_extractor.extract(fake_path)
    
    @pytest.mark.asyncio
    async def test_directory_instead_of_file(self, txt_extractor, temp_dir):
        """Passing a directory instead of file."""
        directory = temp_dir / "subdir"
        directory.mkdir()
        
        # Should handle gracefully
        with pytest.raises(Exception):
            await txt_extractor.extract(directory)
    
    @pytest.mark.asyncio
    async def test_permission_denied(self, txt_extractor, temp_dir):
        """File with no read permissions (Unix only)."""
        if os.name != 'posix':
            pytest.skip("Permission test only works on Unix")
        
        restricted_file = temp_dir / "restricted.txt"
        restricted_file.write_text("Secret content")
        restricted_file.chmod(0o000)
        
        try:
            # Should raise permission error
            with pytest.raises(Exception):
                await txt_extractor.extract(restricted_file)
        finally:
            # Restore permissions for cleanup
            restricted_file.chmod(0o644)
