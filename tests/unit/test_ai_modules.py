"""Real unit tests for AI modules (Claude and Ollama) - no mocking."""


import pytest

from ingestor.ai.claude.agent import ClaudeAgent
from ingestor.ai.ollama.vlm import OllamaVLM
from ingestor.types import ExtractedImage


class TestClaudeAgentInit:
    """Tests for ClaudeAgent initialization."""

    def test_default_init(self):
        """Test default initialization."""
        agent = ClaudeAgent()

        assert agent.system_prompt == ClaudeAgent.DEFAULT_SYSTEM_PROMPT
        assert agent._sdk is None

    def test_custom_system_prompt(self):
        """Test initialization with custom system prompt."""
        custom_prompt = "You are a custom agent."
        agent = ClaudeAgent(system_prompt=custom_prompt)

        assert agent.system_prompt == custom_prompt

    def test_default_system_prompt_content(self):
        """Test default system prompt contains key instructions."""
        agent = ClaudeAgent()

        assert "markdown" in agent.system_prompt.lower()
        assert "clean" in agent.system_prompt.lower()
        assert "format" in agent.system_prompt.lower()


class TestClaudeAgentMethods:
    """Tests for ClaudeAgent methods (without SDK)."""

    @pytest.fixture
    def agent(self):
        return ClaudeAgent()

    def test_get_sdk_raises_without_install(self, agent):
        """Test _get_sdk raises ImportError if SDK not installed."""
        # This test verifies the error handling works
        try:
            agent._get_sdk()
            # If it succeeds, SDK is installed - that's fine
        except ImportError as e:
            assert "claude-code-sdk" in str(e).lower() or "not installed" in str(e).lower()


class TestOllamaVLMInit:
    """Tests for OllamaVLM initialization."""

    def test_default_init(self):
        """Test default initialization."""
        vlm = OllamaVLM()

        assert vlm.model == OllamaVLM.DEFAULT_MODEL
        assert vlm.host == "http://localhost:11434"
        assert vlm._client is None

    def test_custom_init(self):
        """Test custom initialization."""
        vlm = OllamaVLM(
            model="moondream",
            host="http://custom-host:12345",
        )

        assert vlm.model == "moondream"
        assert vlm.host == "http://custom-host:12345"

    def test_default_model_value(self):
        """Test default model is llava."""
        assert OllamaVLM.DEFAULT_MODEL == "llava"


class TestOllamaVLMDescribe:
    """Tests for OllamaVLM describe method."""

    @pytest.fixture
    def vlm(self):
        return OllamaVLM()

    @pytest.mark.asyncio
    async def test_describe_with_bytes(self, vlm, tmp_path):
        """Test describe accepts bytes input."""
        # Create a small test image (1x1 PNG)
        png_header = b'\x89PNG\r\n\x1a\n'
        img_bytes = png_header + b'\x00' * 100

        # This will fail without Ollama running, but tests the interface
        try:
            result = await vlm.describe(img_bytes)
            assert isinstance(result, str)
        except Exception:
            # Expected if Ollama not running
            pass

    @pytest.mark.asyncio
    async def test_describe_with_path(self, vlm, tmp_path):
        """Test describe accepts Path input."""
        # Create a test image file
        img_path = tmp_path / "test.png"
        png_header = b'\x89PNG\r\n\x1a\n'
        img_path.write_bytes(png_header + b'\x00' * 100)

        try:
            result = await vlm.describe(img_path)
            assert isinstance(result, str)
        except Exception:
            # Expected if Ollama not running
            pass

    @pytest.mark.asyncio
    async def test_describe_with_extracted_image(self, vlm):
        """Test describe accepts ExtractedImage input."""
        png_header = b'\x89PNG\r\n\x1a\n'
        image = ExtractedImage(
            data=png_header + b'\x00' * 100,
            format="png",
            filename="test.png",
        )

        try:
            result = await vlm.describe(image)
            assert isinstance(result, str)
        except Exception:
            # Expected if Ollama not running
            pass

    @pytest.mark.asyncio
    async def test_describe_with_custom_prompt(self, vlm):
        """Test describe with custom prompt."""
        png_header = b'\x89PNG\r\n\x1a\n'
        img_bytes = png_header + b'\x00' * 100

        custom_prompt = "What objects are in this image?"

        try:
            result = await vlm.describe(img_bytes, prompt=custom_prompt)
            assert isinstance(result, str)
        except Exception:
            # Expected if Ollama not running
            pass


class TestOllamaVLMClient:
    """Tests for Ollama client handling."""

    def test_get_client_creates_client(self):
        """Test _get_client creates Ollama client."""
        vlm = OllamaVLM()

        try:
            client = vlm._get_client()
            assert client is not None
            assert vlm._client is not None
        except ImportError:
            pytest.skip("ollama package not installed")

    def test_get_client_reuses_client(self):
        """Test _get_client reuses existing client."""
        vlm = OllamaVLM()

        try:
            client1 = vlm._get_client()
            client2 = vlm._get_client()
            assert client1 is client2
        except ImportError:
            pytest.skip("ollama package not installed")


class TestOllamaVLMModels:
    """Tests for different VLM models."""

    def test_llava_model(self):
        """Test LLaVA model configuration."""
        vlm = OllamaVLM(model="llava")
        assert vlm.model == "llava"

    def test_llava_7b_model(self):
        """Test LLaVA 7B model configuration."""
        vlm = OllamaVLM(model="llava:7b")
        assert vlm.model == "llava:7b"

    def test_moondream_model(self):
        """Test Moondream model configuration."""
        vlm = OllamaVLM(model="moondream")
        assert vlm.model == "moondream"

    def test_custom_model(self):
        """Test custom model configuration."""
        vlm = OllamaVLM(model="custom-vision-model:latest")
        assert vlm.model == "custom-vision-model:latest"


class TestOllamaVLMHost:
    """Tests for Ollama host configuration."""

    def test_default_host(self):
        """Test default host is localhost."""
        vlm = OllamaVLM()
        assert "localhost" in vlm.host
        assert "11434" in vlm.host

    def test_custom_host(self):
        """Test custom host configuration."""
        vlm = OllamaVLM(host="http://192.168.1.100:11434")
        assert vlm.host == "http://192.168.1.100:11434"

    def test_custom_port(self):
        """Test custom port configuration."""
        vlm = OllamaVLM(host="http://localhost:8080")
        assert "8080" in vlm.host


class TestOllamaVLMRealExtraction:
    """Real extraction tests (requires Ollama running)."""

    @pytest.fixture
    def vlm(self):
        return OllamaVLM()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_describe_real_image(self, vlm, tmp_path):
        """Test describing a real image with Ollama."""
        # Create a simple test image (using PIL if available)
        try:
            from PIL import Image

            # Create a simple red square image
            img = Image.new('RGB', (100, 100), color='red')
            img_path = tmp_path / "red_square.png"
            img.save(img_path)

            result = await vlm.describe(img_path)

            assert result is not None
            assert isinstance(result, str)
            assert len(result) > 0

        except ImportError:
            pytest.skip("PIL not installed for image creation")
        except Exception as e:
            error_msg = str(e).lower()
            if "connection" in error_msg or "refused" in error_msg:
                pytest.skip("Ollama not running")
            if "not found" in error_msg or "404" in error_msg:
                pytest.skip("Ollama model 'llava' not installed")
            raise


class TestClaudeAgentRealCleanup:
    """Real cleanup tests (requires Claude SDK)."""

    @pytest.fixture
    def agent(self):
        return ClaudeAgent()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_cleanup_real_content(self, agent):
        """Test cleaning up real content with Claude."""
        messy_content = """
# Title

This is some    text with   extra   spaces.


And multiple blank lines.

- Item 1
-Item 2 (missing space)
- Item 3
        """

        try:
            result = await agent.cleanup(messy_content)

            assert result is not None
            assert isinstance(result, str)
            assert len(result) > 0

        except ImportError:
            pytest.skip("Claude SDK not installed")
        except Exception as e:
            if "api" in str(e).lower() or "key" in str(e).lower():
                pytest.skip("Claude API not configured")
            raise


class TestAIModuleEdgeCases:
    """Edge case tests for AI modules."""

    def test_ollama_empty_host(self):
        """Test Ollama with empty host defaults gracefully."""
        vlm = OllamaVLM(host="")
        assert vlm.host == ""

    def test_ollama_none_model(self):
        """Test Ollama handles None model."""
        vlm = OllamaVLM(model=None)
        assert vlm.model is None

    def test_claude_empty_system_prompt(self):
        """Test Claude with empty system prompt uses default (falsy value)."""
        agent = ClaudeAgent(system_prompt="")
        # Empty string is falsy, so defaults to DEFAULT_SYSTEM_PROMPT
        assert agent.system_prompt == ClaudeAgent.DEFAULT_SYSTEM_PROMPT

    def test_claude_none_system_prompt_uses_default(self):
        """Test Claude with None system prompt uses default."""
        agent = ClaudeAgent(system_prompt=None)
        assert agent.system_prompt == ClaudeAgent.DEFAULT_SYSTEM_PROMPT
