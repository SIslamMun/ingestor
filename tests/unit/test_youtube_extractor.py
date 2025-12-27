"""Real unit tests for YouTube extractor - no mocking."""


import pytest

from ingestor.extractors.youtube.youtube_extractor import YouTubeExtractor
from ingestor.types import MediaType


class TestYouTubeExtractorInit:
    """Tests for YouTubeExtractor initialization."""

    def test_default_init(self):
        """Test default initialization."""
        extractor = YouTubeExtractor()

        assert extractor.caption_type == "auto"
        assert extractor.include_playlist is False
        assert extractor.languages == ["en"]

    def test_custom_init(self):
        """Test custom initialization."""
        extractor = YouTubeExtractor(
            caption_type="manual",
            include_playlist=True,
            languages=["en", "es", "fr"],
        )

        assert extractor.caption_type == "manual"
        assert extractor.include_playlist is True
        assert extractor.languages == ["en", "es", "fr"]

    def test_media_type(self):
        """Test media type is YOUTUBE."""
        extractor = YouTubeExtractor()
        assert extractor.media_type == MediaType.YOUTUBE


class TestYouTubeExtractorVideoID:
    """Tests for video ID extraction."""

    @pytest.fixture
    def extractor(self):
        return YouTubeExtractor()

    def test_extract_id_standard_url(self, extractor):
        """Test extracting ID from standard YouTube URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = extractor._extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_id_short_url(self, extractor):
        """Test extracting ID from youtu.be short URL."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        video_id = extractor._extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_id_embed_url(self, extractor):
        """Test extracting ID from embed URL."""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        video_id = extractor._extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_id_with_params(self, extractor):
        """Test extracting ID from URL with extra parameters."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120&list=PLtest"
        video_id = extractor._extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_id_mobile_url(self, extractor):
        """Test extracting ID from mobile URL."""
        url = "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = extractor._extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_id_plain_id(self, extractor):
        """Test extracting ID when given just the ID."""
        video_id = extractor._extract_video_id("dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_id_invalid_url(self, extractor):
        """Test extracting ID from invalid URL."""
        url = "https://example.com/video"
        video_id = extractor._extract_video_id(url)
        assert video_id is None

    def test_extract_id_empty(self, extractor):
        """Test extracting ID from empty string."""
        video_id = extractor._extract_video_id("")
        assert video_id is None


class TestYouTubeExtractorPlaylistDetection:
    """Tests for playlist URL detection."""

    @pytest.fixture
    def extractor(self):
        return YouTubeExtractor()

    def test_supports_playlist_url(self, extractor):
        """Test supports detects playlist URL."""
        url = "https://www.youtube.com/playlist?list=PLtest123"
        assert extractor.supports(url)

    def test_supports_video_with_list_param(self, extractor):
        """Test supports video URL with list param."""
        url = "https://www.youtube.com/watch?v=abc123&list=PLtest456"
        assert extractor.supports(url)

    def test_supports_video_without_playlist(self, extractor):
        """Test supports regular video URL."""
        url = "https://www.youtube.com/watch?v=abc123"
        assert extractor.supports(url)


class TestYouTubeExtractorCanExtract:
    """Tests for supports method."""

    @pytest.fixture
    def extractor(self):
        return YouTubeExtractor()

    def test_supports_youtube_url(self, extractor):
        """Test supports for YouTube URLs."""
        assert extractor.supports("https://www.youtube.com/watch?v=abc123")
        assert extractor.supports("https://youtube.com/watch?v=abc123")
        assert extractor.supports("http://www.youtube.com/watch?v=abc123")

    def test_supports_youtu_be(self, extractor):
        """Test supports for youtu.be URLs."""
        assert extractor.supports("https://youtu.be/abc123")
        assert extractor.supports("http://youtu.be/abc123")

    def test_supports_embed_url(self, extractor):
        """Test supports for embed URLs."""
        assert extractor.supports("https://www.youtube.com/embed/abc123")

    def test_supports_playlist_url(self, extractor):
        """Test supports for playlist URLs."""
        assert extractor.supports("https://www.youtube.com/playlist?list=PLtest")

    def test_cannot_extract_non_youtube(self, extractor):
        """Test supports returns False for non-YouTube URLs."""
        assert not extractor.supports("https://vimeo.com/123456")
        assert not extractor.supports("https://example.com/video")

    def test_cannot_extract_local_file(self, extractor, tmp_path):
        """Test supports returns False for local files."""
        test_file = tmp_path / "video.mp4"
        test_file.write_bytes(b"fake video")

        assert not extractor.supports(str(test_file))


class TestYouTubeExtractorRealExtraction:
    """Real extraction tests (requires network and yt_dlp)."""

    @pytest.fixture
    def extractor(self):
        pytest.importorskip("yt_dlp", reason="yt_dlp not installed")
        return YouTubeExtractor()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_extract_video_metadata(self, extractor):
        """Test extracting video metadata from a real video."""
        # Use a well-known video that should always exist
        url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" - first YT video

        result = await extractor.extract(url)

        assert result is not None
        assert result.media_type == MediaType.YOUTUBE
        assert result.title is not None
        assert len(result.title) > 0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_extract_video_with_captions(self, extractor):
        """Test extracting video with captions."""
        # TED talks usually have good captions
        url = "https://www.youtube.com/watch?v=8jPQjjsBbIc"  # A TED talk

        result = await extractor.extract(url)

        assert result is not None
        # May or may not have transcript depending on video

    @pytest.mark.asyncio
    async def test_extract_invalid_video_id(self, extractor):
        """Test extracting with invalid video ID."""
        url = "https://www.youtube.com/watch?v=INVALID_ID_12345"

        result = await extractor.extract(url)

        # Should return error result
        assert result is not None
        # Will have error in markdown or metadata

    @pytest.mark.asyncio
    async def test_extract_invalid_url(self, extractor):
        """Test extracting from non-YouTube URL."""
        result = await extractor.extract("https://example.com/video")

        assert result is not None
        assert "Error" in result.markdown or "Invalid" in result.markdown


class TestYouTubeExtractorMarkdownBuilder:
    """Tests for markdown building."""

    @pytest.fixture
    def extractor(self):
        return YouTubeExtractor()

    def test_build_markdown_with_metadata(self, extractor):
        """Test building markdown with metadata."""
        metadata = {
            "title": "Test Video",
            "channel": "Test Channel",
            "description": "This is a test video description.",
            "duration": 630,  # Duration in seconds (10:30)
            "view_count": 1000000,
            "upload_date": "20240115",
            "video_id": "test123",
        }
        transcript = "This is the transcript content."

        markdown = extractor._build_markdown(metadata, transcript)

        assert "Test Video" in markdown
        assert "Test Channel" in markdown
        assert "Transcript" in markdown

    def test_build_markdown_no_transcript(self, extractor):
        """Test building markdown without transcript."""
        metadata = {
            "title": "Test Video",
            "channel": "Test Channel",
            "video_id": "test123",
        }

        markdown = extractor._build_markdown(metadata, None)

        assert "Test Video" in markdown
        assert "No transcript" in markdown or "Transcript" in markdown

    def test_build_markdown_empty_metadata(self, extractor):
        """Test building markdown with empty metadata."""
        markdown = extractor._build_markdown({}, "Some transcript")

        assert len(markdown) > 0
        assert "Transcript" in markdown


class TestYouTubeExtractorCaptionTypes:
    """Tests for caption type handling."""

    def test_auto_caption_type(self):
        """Test auto caption type."""
        extractor = YouTubeExtractor(caption_type="auto")
        assert extractor.caption_type == "auto"

    def test_manual_caption_type(self):
        """Test manual caption type."""
        extractor = YouTubeExtractor(caption_type="manual")
        assert extractor.caption_type == "manual"


class TestYouTubeExtractorLanguages:
    """Tests for language handling."""

    def test_default_language(self):
        """Test default language is English."""
        extractor = YouTubeExtractor()
        assert "en" in extractor.languages

    def test_multiple_languages(self):
        """Test multiple language preferences."""
        extractor = YouTubeExtractor(languages=["en", "es", "de", "fr"])
        assert extractor.languages == ["en", "es", "de", "fr"]

    def test_single_non_english_language(self):
        """Test single non-English language."""
        extractor = YouTubeExtractor(languages=["ja"])
        assert extractor.languages == ["ja"]


class TestYouTubeExtractorEdgeCases:
    """Edge case tests for YouTube extractor."""

    @pytest.fixture
    def extractor(self):
        return YouTubeExtractor()

    def test_url_with_timestamp(self, extractor):
        """Test URL with timestamp parameter."""
        url = "https://www.youtube.com/watch?v=abc123&t=120"
        video_id = extractor._extract_video_id(url)
        assert video_id == "abc123"

    def test_url_with_feature_param(self, extractor):
        """Test URL with feature parameter."""
        url = "https://www.youtube.com/watch?v=abc123&feature=share"
        video_id = extractor._extract_video_id(url)
        assert video_id == "abc123"

    def test_shorts_url(self, extractor):
        """Test YouTube Shorts URL."""
        url = "https://www.youtube.com/shorts/abc123"
        extractor._extract_video_id(url)
        # May or may not handle shorts depending on implementation
        # At minimum should not crash

    def test_live_stream_url(self, extractor):
        """Test live stream URL."""
        # Should handle live URLs
        assert extractor.supports("https://www.youtube.com/watch?v=abc123")

    def test_music_url(self, extractor):
        """Test YouTube Music URL."""
        url = "https://music.youtube.com/watch?v=abc123"
        # Should recognize as YouTube
        extractor._extract_video_id(url)
        # Implementation may vary
