"""Integration tests for VLM image descriptions."""

from unittest.mock import MagicMock, patch

import pytest

from ingestor.types import ExtractedImage


class TestVLMDescriber:
    """Tests for VLM image description functionality."""

    @pytest.fixture
    def vlm(self):
        """Create VLM instance, skip if ollama not installed."""
        try:
            from ingestor.ai.ollama.vlm import OllamaVLM
            return OllamaVLM(model="llava")
        except ImportError:
            pytest.skip("ollama not installed")

    @pytest.fixture
    def sample_image_bytes(self, sample_png) -> bytes:
        """Get sample image bytes."""
        if not sample_png.exists():
            pytest.skip("Image fixture not generated")
        return sample_png.read_bytes()

    @pytest.fixture
    def extracted_image(self, sample_image_bytes) -> ExtractedImage:
        """Create an ExtractedImage for testing."""
        return ExtractedImage(
            filename="test.png",
            data=sample_image_bytes,
            format="png",
        )

    def test_vlm_initialization(self, vlm):
        """Test VLM initializes with correct settings."""
        assert vlm.model == "llava"
        assert vlm.host == "http://localhost:11434"

    @pytest.mark.asyncio
    async def test_is_available_without_ollama(self, vlm):
        """Test is_available returns False when Ollama not running."""
        # Mock the client to simulate connection failure
        with patch.object(vlm, '_get_client') as mock_client:
            mock_client.side_effect = Exception("Connection refused")
            result = await vlm.is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_describe_with_mock(self, vlm, extracted_image):
        """Test describe with mocked Ollama response."""
        mock_response = {"response": "A red square image with transparency."}

        with patch.object(vlm, '_get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.generate.return_value = mock_response
            mock_get_client.return_value = mock_client

            description = await vlm.describe(extracted_image)

            assert description == "A red square image with transparency."
            mock_client.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_describe_batch_with_mock(self, vlm, extracted_image):
        """Test batch description with mocked responses."""
        images = [extracted_image, extracted_image]
        mock_response = {"response": "Test description."}

        with patch.object(vlm, '_get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.generate.return_value = mock_response
            mock_get_client.return_value = mock_client

            results = await vlm.describe_batch(images)

            assert len(results) == 2
            assert all(img.description == "Test description." for img in results)

    @pytest.mark.asyncio
    async def test_describe_handles_error(self, vlm, extracted_image):
        """Test describe handles Ollama errors gracefully."""
        images = [extracted_image]

        with patch.object(vlm, '_get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.generate.side_effect = Exception("Model not found")
            mock_get_client.return_value = mock_client

            results = await vlm.describe_batch(images)

            # Should not raise, description should be None
            assert len(results) == 1
            assert results[0].description is None

    @pytest.mark.asyncio
    async def test_describe_from_path(self, vlm, sample_png):
        """Test describing image from file path."""
        if not sample_png.exists():
            pytest.skip("Image fixture not generated")

        mock_response = {"response": "Image from file."}

        with patch.object(vlm, '_get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.generate.return_value = mock_response
            mock_get_client.return_value = mock_client

            description = await vlm.describe(sample_png)

            assert description == "Image from file."

    @pytest.mark.asyncio
    async def test_describe_from_bytes(self, vlm, sample_image_bytes):
        """Test describing image from raw bytes."""
        mock_response = {"response": "Image from bytes."}

        with patch.object(vlm, '_get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.generate.return_value = mock_response
            mock_get_client.return_value = mock_client

            description = await vlm.describe(sample_image_bytes)

            assert description == "Image from bytes."

    @pytest.mark.asyncio
    async def test_custom_prompt(self, vlm, extracted_image):
        """Test using custom prompt for description."""
        custom_prompt = "What color is this image?"
        mock_response = {"response": "Red."}

        with patch.object(vlm, '_get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.generate.return_value = mock_response
            mock_get_client.return_value = mock_client

            description = await vlm.describe(extracted_image, prompt=custom_prompt)

            assert description == "Red."
            # Verify custom prompt was used
            call_args = mock_client.generate.call_args
            assert call_args.kwargs.get('prompt') == custom_prompt


@pytest.mark.network
class TestVLMLive:
    """Live tests that require Ollama running.

    Run with: pytest --network -m network
    """

    @pytest.fixture
    def vlm(self):
        try:
            from ingestor.ai.ollama.vlm import OllamaVLM
            return OllamaVLM(model="llava")
        except ImportError:
            pytest.skip("ollama not installed")

    @pytest.mark.asyncio
    async def test_live_describe(self, vlm, sample_png):
        """Test live VLM description (requires Ollama running with llava)."""
        if not sample_png.exists():
            pytest.skip("Image fixture not generated")

        if not await vlm.is_available():
            pytest.skip("Ollama not running or llava model not available")

        description = await vlm.describe(sample_png)

        assert description
        assert len(description) > 10  # Should have meaningful content
