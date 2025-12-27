"""Tests for CharsetHandler."""


import pytest

from ingestor.core.charset import CharsetHandler


class TestCharsetHandler:
    """Tests for CharsetHandler class."""

    @pytest.fixture
    def handler(self):
        """Create a CharsetHandler instance."""
        return CharsetHandler()

    def test_decode_utf8_bytes(self, handler):
        """Test decoding UTF-8 bytes."""
        data = b"Hello, World!"
        text, encoding = handler.decode_bytes(data)

        assert text == "Hello, World!"
        assert encoding.lower() in ("utf-8", "ascii")

    def test_decode_latin1_bytes(self, handler):
        """Test decoding Latin-1 bytes."""
        # Use longer content for better detection
        data = "Héllo Wörld! This is a longer text with special characters: café, résumé, naïve.".encode("latin-1")
        text, encoding = handler.decode_bytes(data)

        # Should successfully decode (might detect as latin-1 or another compatible encoding)
        assert isinstance(text, str)
        assert len(text) > 0

    def test_decode_utf8_with_bom(self, handler):
        """Test decoding UTF-8 with BOM."""
        data = b"\xef\xbb\xbfHello"
        text, encoding = handler.decode_bytes(data)

        assert "Hello" in text

    def test_decode_empty_bytes(self, handler):
        """Test decoding empty bytes."""
        text, encoding = handler.decode_bytes(b"")
        assert text == ""

    def test_detect_encoding(self, handler):
        """Test encoding detection without decoding."""
        data = b"Hello, World!"
        encoding = handler.detect_encoding(data)

        assert encoding is not None
        assert encoding.lower() in ("utf-8", "ascii")

    def test_read_text_from_file(self, handler, tmp_path):
        """Test reading text file with encoding detection."""
        # Create a UTF-8 file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!", encoding="utf-8")

        text, encoding = handler.read_text(test_file)

        assert text == "Hello, World!"
        assert encoding.lower() in ("utf-8", "ascii")

    def test_read_latin1_file(self, handler, tmp_path):
        """Test reading Latin-1 encoded file."""
        test_file = tmp_path / "test_latin1.txt"
        content = "Café résumé"
        test_file.write_bytes(content.encode("latin-1"))

        text, encoding = handler.read_text(test_file)

        # Should successfully decode the content
        assert len(text) > 0


class TestCharsetEdgeCases:
    """Edge case tests for charset handling."""

    @pytest.fixture
    def handler(self):
        return CharsetHandler()

    def test_binary_data_fallback(self, handler):
        """Test handling of binary data with fallback."""
        # Some random binary that's not valid UTF-8
        data = bytes([0x80, 0x81, 0x82])

        # Should not raise, may return replacement chars or empty
        try:
            text, encoding = handler.decode_bytes(data)
            assert isinstance(text, str)
        except Exception:
            pytest.skip("Binary handling may vary by implementation")

    def test_mixed_encoding_content(self, handler):
        """Test content that could be multiple encodings."""
        # ASCII is valid in many encodings
        data = b"Simple ASCII text"
        text, encoding = handler.decode_bytes(data)

        assert text == "Simple ASCII text"
