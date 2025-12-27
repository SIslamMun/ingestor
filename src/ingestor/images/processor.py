"""Unified image processing pipeline."""

from pathlib import Path
from typing import Any

from ..types import ExtractedImage, IngestConfig
from .converter import ImageConverter


class ImageProcessor:
    """Process extracted images through the pipeline.

    Handles:
    - Format conversion (to PNG by default)
    - Naming standardization
    - Optional VLM description generation
    """

    def __init__(self, config: IngestConfig | None = None):
        """Initialize the processor.

        Args:
            config: Configuration options
        """
        self.config = config or IngestConfig()

        # Initialize converter unless keeping raw formats
        if not self.config.keep_raw_images:
            self.converter: ImageConverter | None = ImageConverter(self.config.target_image_format)
        else:
            self.converter = None

        # VLM describer (lazy loaded)
        self._vlm_describer: Any = None

    @property
    def vlm_describer(self) -> Any:
        """Lazy load VLM describer."""
        if self._vlm_describer is None and self.config.describe_images:
            try:
                from ..ai.ollama.vlm import VLMDescriber
                self._vlm_describer = VLMDescriber(
                    host=self.config.ollama_host,
                    model=self.config.vlm_model,
                )
            except ImportError:
                pass
        return self._vlm_describer

    async def process(
        self,
        images: list[ExtractedImage],
        source_name: str = "document",
    ) -> list[ExtractedImage]:
        """Process a list of images through the pipeline.

        Args:
            images: Images to process
            source_name: Name of the source document (for naming)

        Returns:
            Processed images
        """
        processed = []

        for i, image in enumerate(images, 1):
            # Standardize filename
            processed_image = self._standardize_filename(image, source_name, i)

            # Convert format if needed
            if self.converter is not None:
                processed_image = self.converter.convert(processed_image)

            # Generate VLM description if enabled
            if self.config.describe_images and self.vlm_describer is not None:
                try:
                    description = await self.vlm_describer.describe(
                        processed_image,
                        context=processed_image.context or "",
                    )
                    processed_image = ExtractedImage(
                        filename=processed_image.filename,
                        data=processed_image.data,
                        format=processed_image.format,
                        page=processed_image.page,
                        caption=processed_image.caption,
                        context=processed_image.context,
                        description=description,
                    )
                except Exception:
                    pass  # Skip VLM if it fails

            processed.append(processed_image)

        return processed

    def _standardize_filename(
        self,
        image: ExtractedImage,
        source_name: str,
        index: int,
    ) -> ExtractedImage:
        """Standardize image filename.

        Format: {source_name}_img_{index:03d}.{ext}

        Args:
            image: Image to rename
            source_name: Name of source document
            index: Image index

        Returns:
            Image with standardized filename
        """
        # Clean source name
        clean_name = Path(source_name).stem
        clean_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in clean_name)

        # Get extension
        ext = image.format.lower()
        if ext == "jpeg":
            ext = "jpg"

        new_filename = f"{clean_name}_img_{index:03d}.{ext}"

        return ExtractedImage(
            filename=new_filename,
            data=image.data,
            format=image.format,
            page=image.page,
            caption=image.caption,
            context=image.context,
            description=image.description,
        )

    def process_sync(
        self,
        images: list[ExtractedImage],
        source_name: str = "document",
    ) -> list[ExtractedImage]:
        """Process images synchronously (no VLM).

        Args:
            images: Images to process
            source_name: Name of the source document

        Returns:
            Processed images
        """
        processed = []

        for i, image in enumerate(images, 1):
            processed_image = self._standardize_filename(image, source_name, i)

            if self.converter is not None:
                processed_image = self.converter.convert(processed_image)

            processed.append(processed_image)

        return processed
