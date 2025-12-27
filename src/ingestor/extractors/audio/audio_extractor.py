"""Audio extractor using OpenAI Whisper for transcription."""

from pathlib import Path

from ...types import ExtractionResult, MediaType
from ..base import BaseExtractor


class AudioExtractor(BaseExtractor):
    """Extract transcriptions from audio files using OpenAI Whisper.

    Supports various audio formats including MP3, WAV, FLAC, M4A, etc.
    Uses local Whisper models for transcription.
    """

    media_type = MediaType.AUDIO

    # Supported audio extensions
    AUDIO_EXTENSIONS = {
        ".mp3", ".wav", ".flac", ".m4a", ".ogg", ".opus",
        ".wma", ".aac", ".aiff", ".webm",
    }

    def __init__(self, model: str = "turbo"):
        """Initialize audio extractor.

        Args:
            model: Whisper model to use (tiny, base, small, medium, large, turbo)
        """
        self.model_name = model
        self._model = None

    def _load_model(self):
        """Lazy load the Whisper model."""
        if self._model is None:
            import whisper
            self._model = whisper.load_model(self.model_name)
        return self._model

    async def extract(self, source: str | Path) -> ExtractionResult:
        """Extract transcription from an audio file.

        Args:
            source: Path to the audio file

        Returns:
            Extraction result with transcribed text
        """
        path = Path(source)

        # Load model and transcribe
        model = self._load_model()
        result = model.transcribe(str(path))

        # Get transcription details
        text = result.get("text", "").strip()
        language = result.get("language", "unknown")
        segments = result.get("segments", [])

        # Build markdown with timestamps
        markdown = self._build_markdown(path, text, language, segments)

        # Calculate duration from segments
        duration = None
        if segments:
            duration = segments[-1].get("end", 0)

        return ExtractionResult(
            markdown=markdown,
            title=path.stem,
            source=str(path),
            media_type=MediaType.AUDIO,
            images=[],
            metadata={
                "language": language,
                "duration": duration,
                "segment_count": len(segments),
                "model": self.model_name,
            },
        )

    def _build_markdown(
        self,
        path: Path,
        text: str,
        language: str,
        segments: list,
    ) -> str:
        """Build markdown from transcription.

        Args:
            path: Source file path
            text: Full transcription text
            language: Detected language
            segments: Whisper segments with timestamps

        Returns:
            Markdown content
        """
        lines = [
            f"# Audio Transcription: {path.name}",
            "",
            f"**Source:** {path.name}",
            f"**Language:** {language}",
        ]

        if segments:
            duration = segments[-1].get("end", 0)
            hours, remainder = divmod(int(duration), 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                lines.append(f"**Duration:** {hours}h {minutes}m {seconds}s")
            else:
                lines.append(f"**Duration:** {minutes}m {seconds}s")

        lines.append("")
        lines.append("## Transcript")
        lines.append("")

        if text:
            lines.append(text)
        else:
            lines.append("*No speech detected in audio.*")

        # Optionally include timestamped segments
        if segments and len(segments) > 1:
            lines.append("")
            lines.append("## Timestamped Segments")
            lines.append("")

            for segment in segments:
                start = segment.get("start", 0)
                end = segment.get("end", 0)
                segment_text = segment.get("text", "").strip()

                start_str = self._format_timestamp(start)
                end_str = self._format_timestamp(end)

                lines.append(f"**[{start_str} - {end_str}]** {segment_text}")
                lines.append("")

        return "\n".join(lines)

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to timestamp string.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp (MM:SS or HH:MM:SS)
        """
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)

        if hours:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def supports(self, source: str | Path) -> bool:
        """Check if this extractor handles the source.

        Args:
            source: Path to check

        Returns:
            True if this is an audio file
        """
        suffix = Path(source).suffix.lower()
        return suffix in self.AUDIO_EXTENSIONS
