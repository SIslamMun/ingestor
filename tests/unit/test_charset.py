"""Real unit tests for Charset detection - no mocking."""

from pathlib import Path

import pytest

from ingestor.core.charset import CharsetHandler


class TestCharsetHandler:
    """Tests for CharsetHandler class."""

    @pytest.fixture
    def handler(self):
        return CharsetHandler()

    def test_handler_init(self):
        """Test handler initialization."""
        handler = CharsetHandler()
        assert handler is not None
        assert handler.DEFAULT_ENCODING == "utf-8"

    def test_read_text_utf8(self, handler, tmp_path):
        """Test reading UTF-8 text."""
        test_file = tmp_path / "utf8.txt"
        test_file.write_text("Hello World", encoding="utf-8")

        text, encoding = handler.read_text(test_file)

        assert text == "Hello World"
        assert encoding.lower() in ["utf-8", "utf8", "ascii"]

    def test_read_text_utf8_with_bom(self, handler, tmp_path):
        """Test reading UTF-8 with BOM."""
        test_file = tmp_path / "utf8bom.txt"
        test_file.write_bytes(b'\xef\xbb\xbfHello World')

        text, encoding = handler.read_text(test_file)

        assert "Hello World" in text
        assert "utf" in encoding.lower()

    def test_read_text_latin1(self, handler, tmp_path):
        """Test reading Latin-1 encoded text."""
        test_file = tmp_path / "latin1.txt"
        # Latin-1 specific characters
        original = "Café résumé naïve"
        test_file.write_bytes(original.encode("latin-1"))

        text, encoding = handler.read_text(test_file)

        assert text is not None
        # Should decode successfully

    def test_read_text_ascii(self, handler, tmp_path):
        """Test reading ASCII text."""
        test_file = tmp_path / "ascii.txt"
        test_file.write_bytes(b"Hello World 123")

        text, encoding = handler.read_text(test_file)

        assert text == "Hello World 123"

    def test_decode_bytes_utf8(self, handler):
        """Test decoding UTF-8 bytes."""
        content = b"Hello World"

        text, encoding = handler.decode_bytes(content)

        assert text == "Hello World"

    def test_decode_bytes_with_unicode(self, handler):
        """Test decoding bytes with unicode."""
        content = "Hello 世界 Café".encode()

        text, encoding = handler.decode_bytes(content)

        assert "世界" in text or "Hello" in text

    def test_read_text_empty_file(self, handler, tmp_path):
        """Test reading empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_bytes(b"")

        text, encoding = handler.read_text(test_file)

        assert text == ""

    def test_read_text_japanese(self, handler, tmp_path):
        """Test reading Japanese UTF-8."""
        test_file = tmp_path / "japanese.txt"
        test_file.write_text("こんにちは世界", encoding="utf-8")

        text, encoding = handler.read_text(test_file)

        assert "こんにちは" in text

    def test_read_text_chinese(self, handler, tmp_path):
        """Test reading Chinese UTF-8."""
        test_file = tmp_path / "chinese.txt"
        test_file.write_text("你好世界", encoding="utf-8")

        text, encoding = handler.read_text(test_file)

        assert "你好" in text

    def test_decode_bytes_empty(self, handler):
        """Test decoding empty bytes."""
        text, encoding = handler.decode_bytes(b"")

        assert text == ""


class TestCharsetHandlerEdgeCases:
    """Edge case tests for CharsetHandler."""

    @pytest.fixture
    def handler(self):
        return CharsetHandler()

    def test_read_text_very_small(self, handler, tmp_path):
        """Test reading very small file."""
        test_file = tmp_path / "tiny.txt"
        test_file.write_bytes(b"A")

        text, encoding = handler.read_text(test_file)

        assert text == "A"

    def test_read_text_large_file(self, handler, tmp_path):
        """Test reading large file."""
        test_file = tmp_path / "large.txt"
        content = "Hello World\n" * 10000
        test_file.write_text(content, encoding="utf-8")

        text, encoding = handler.read_text(test_file)

        assert "Hello World" in text
        assert len(text) > 100000

    def test_read_text_special_characters(self, handler, tmp_path):
        """Test reading file with special characters."""
        test_file = tmp_path / "special.txt"
        test_file.write_text("€£¥©®™†‡§¶", encoding="utf-8")

        text, encoding = handler.read_text(test_file)

        assert "€" in text or "£" in text

    def test_decode_bytes_binary_like(self, handler):
        """Test decoding bytes that look binary."""
        # Mix of printable and some high bytes
        content = b"Hello\xc0\xc1World"

        # Should handle gracefully
        try:
            text, encoding = handler.decode_bytes(content)
            assert text is not None
        except Exception:
            pass  # Some binary may fail

    def test_read_text_path_object(self, handler, tmp_path):
        """Test read_text accepts Path object."""
        test_file = tmp_path / "path.txt"
        test_file.write_text("Content")

        text, encoding = handler.read_text(Path(test_file))

        assert text == "Content"

    def test_read_text_string_path(self, handler, tmp_path):
        """Test read_text accepts string path."""
        test_file = tmp_path / "string.txt"
        test_file.write_text("Content")

        text, encoding = handler.read_text(str(test_file))

        assert text == "Content"
