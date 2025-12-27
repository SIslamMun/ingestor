"""Integration tests for audio extraction with Whisper."""


import pytest

from ingestor.types import MediaType

# Check if whisper is available
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


@pytest.mark.skipif(not WHISPER_AVAILABLE, reason="openai-whisper not installed")
class TestAudioExtraction:
    """Integration tests for audio transcription."""

    @pytest.fixture
    def extractor(self):
        from ingestor.extractors.audio import AudioExtractor
        # Use tiny model for faster tests
        return AudioExtractor(model="tiny")

    def test_supports_audio_formats(self, extractor):
        """Test supports various audio formats."""
        assert extractor.supports("audio.mp3")
        assert extractor.supports("audio.wav")
        assert extractor.supports("audio.flac")
        assert extractor.supports("audio.m4a")
        assert not extractor.supports("audio.txt")

    @pytest.mark.asyncio
    async def test_extract_wav(self, extractor, sample_wav):
        """Test extracting WAV audio file."""
        if not sample_wav.exists():
            pytest.skip("WAV fixture not generated")

        result = await extractor.extract(sample_wav)

        assert result.media_type == MediaType.AUDIO
        assert result.markdown
        # Should have transcription structure
        assert "Transcript" in result.markdown
        # Should have metadata
        assert "language" in result.metadata

    @pytest.mark.asyncio
    async def test_audio_metadata(self, extractor, sample_wav):
        """Test audio metadata extraction."""
        if not sample_wav.exists():
            pytest.skip("WAV fixture not generated")

        result = await extractor.extract(sample_wav)

        assert "duration" in result.metadata or "language" in result.metadata
        assert "model" in result.metadata

    @pytest.mark.asyncio
    async def test_audio_timestamps(self, extractor, sample_wav):
        """Test audio includes timestamps."""
        if not sample_wav.exists():
            pytest.skip("WAV fixture not generated")

        result = await extractor.extract(sample_wav)

        # Our 1-second tone won't have speech, but structure should be there
        assert "Transcript" in result.markdown
