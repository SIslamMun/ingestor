"""Ollama VLM for generating image descriptions."""

import base64
from pathlib import Path
from typing import Any

from ...types import ExtractedImage


class OllamaVLM:
    """Vision Language Model client using Ollama.

    Generates natural language descriptions of images using
    models like LLaVA, Moondream, or other vision models.
    """

    DEFAULT_MODEL = "llava"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        host: str = "http://localhost:11434",
    ):
        """Initialize Ollama VLM client.

        Args:
            model: Ollama vision model name (llava, moondream, etc.)
            host: Ollama server URL
        """
        self.model = model
        self.host = host
        self._client: Any = None

    def _get_client(self) -> Any:
        """Get or create Ollama client."""
        if self._client is None:
            import ollama
            self._client = ollama.Client(host=self.host)
        return self._client

    async def describe(
        self,
        image: ExtractedImage | Path | bytes,
        prompt: str | None = None,
    ) -> str:
        """Generate a description for an image.

        Args:
            image: Image to describe (ExtractedImage, path, or bytes)
            prompt: Custom prompt for description

        Returns:
            Generated description
        """
        # Get image bytes
        if isinstance(image, ExtractedImage):
            img_bytes = image.data
        elif isinstance(image, Path):
            img_bytes = image.read_bytes()
        else:
            img_bytes = image

        # Encode to base64
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")

        # Default prompt
        if prompt is None:
            prompt = (
                "Describe this image in detail. Include information about: "
                "1) Main subject or content, "
                "2) Visual elements (colors, composition, style), "
                "3) Any text visible in the image, "
                "4) Context or setting if apparent. "
                "Be concise but thorough."
            )

        client = self._get_client()

        response = client.generate(
            model=self.model,
            prompt=prompt,
            images=[img_b64],
        )

        return response.get("response", "").strip()

    async def describe_file(
        self,
        path: Path,
        prompt: str | None = None,
    ) -> str:
        """Generate a description for an image file.

        Args:
            path: Path to the image file
            prompt: Custom prompt for description

        Returns:
            Generated description
        """
        return await self.describe(path, prompt)

    async def describe_batch(
        self,
        images: list[ExtractedImage],
        prompt: str | None = None,
    ) -> list[ExtractedImage]:
        """Generate descriptions for multiple images.

        Args:
            images: List of images to describe
            prompt: Custom prompt for descriptions

        Returns:
            Images with descriptions added
        """
        for image in images:
            try:
                description = await self.describe(image, prompt)
                image.description = description
            except Exception:
                image.description = None

        return images

    async def is_available(self) -> bool:
        """Check if Ollama is available and model is loaded.

        Returns:
            True if Ollama is reachable and model exists
        """
        try:
            client = self._get_client()
            models = client.list()
            model_names = [m.get("name", "").split(":")[0] for m in models.get("models", [])]
            return self.model.split(":")[0] in model_names
        except Exception:
            return False

    async def pull_model(self) -> bool:
        """Pull the configured model if not available.

        Returns:
            True if model is now available
        """
        try:
            client = self._get_client()
            client.pull(self.model)
            return True
        except Exception:
            return False


async def describe_images(
    images: list[ExtractedImage],
    model: str = OllamaVLM.DEFAULT_MODEL,
    host: str = "http://localhost:11434",
) -> list[ExtractedImage]:
    """Convenience function to describe multiple images.

    Args:
        images: Images to describe
        model: Ollama model to use
        host: Ollama server URL

    Returns:
        Images with descriptions
    """
    vlm = OllamaVLM(model=model, host=host)
    return await vlm.describe_batch(images)


# Alias for backwards compatibility
VLMDescriber = OllamaVLM
