"""Charset detection and handling using charset_normalizer."""

from pathlib import Path

from charset_normalizer import from_bytes, from_path


class CharsetHandler:
    """Handle charset detection and text decoding for non-UTF8 content.

    Uses charset_normalizer for accurate encoding detection across
    various languages and character sets.
    """

    DEFAULT_ENCODING = "utf-8"

    def read_text(self, path: str | Path) -> tuple[str, str]:
        """Read text from a file with automatic charset detection.

        Args:
            path: Path to the file

        Returns:
            Tuple of (decoded_text, detected_encoding)
        """
        path = Path(path)

        try:
            result = from_path(path).best()
            if result is not None:
                return str(result), result.encoding or self.DEFAULT_ENCODING
        except Exception:
            pass

        # Fallback to UTF-8
        try:
            text = path.read_text(encoding=self.DEFAULT_ENCODING)
            return text, self.DEFAULT_ENCODING
        except UnicodeDecodeError:
            # Try latin-1 as last resort (accepts any byte)
            text = path.read_text(encoding="latin-1")
            return text, "latin-1"

    def decode_bytes(self, data: bytes) -> tuple[str, str]:
        """Decode bytes with automatic charset detection.

        Args:
            data: Raw bytes to decode

        Returns:
            Tuple of (decoded_text, detected_encoding)
        """
        try:
            result = from_bytes(data).best()
            if result is not None:
                return str(result), result.encoding or self.DEFAULT_ENCODING
        except Exception:
            pass

        # Fallback to UTF-8
        try:
            return data.decode(self.DEFAULT_ENCODING), self.DEFAULT_ENCODING
        except UnicodeDecodeError:
            # Try latin-1 as last resort
            return data.decode("latin-1"), "latin-1"

    def detect_encoding(self, data: bytes) -> str | None:
        """Detect the encoding of raw bytes without decoding.

        Args:
            data: Raw bytes to analyze

        Returns:
            Detected encoding name or None
        """
        try:
            result = from_bytes(data).best()
            if result is not None:
                return result.encoding
        except Exception:
            pass
        return None

    def detect_encoding_from_file(self, path: str | Path) -> str | None:
        """Detect the encoding of a file without reading it fully.

        Args:
            path: Path to the file

        Returns:
            Detected encoding name or None
        """
        path = Path(path)
        try:
            result = from_path(path).best()
            if result is not None:
                return result.encoding
        except Exception:
            pass
        return None
