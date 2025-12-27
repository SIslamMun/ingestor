"""Image format conversion."""

from io import BytesIO

from PIL import Image
from PIL.Image import Image as PILImage

from ..types import ExtractedImage


class ImageConverter:
    """Convert images to a target format (default: PNG).

    Handles format conversion while preserving image quality.
    """

    # Supported target formats
    SUPPORTED_FORMATS = {"png", "jpeg", "jpg", "webp", "gif", "bmp", "tiff"}

    def __init__(self, target_format: str = "png"):
        """Initialize the converter.

        Args:
            target_format: Target format to convert images to
        """
        self.target_format = target_format.lower()
        if self.target_format == "jpg":
            self.target_format = "jpeg"

        if self.target_format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {target_format}")

    def convert(self, image: ExtractedImage) -> ExtractedImage:
        """Convert an image to the target format.

        Args:
            image: Image to convert

        Returns:
            Converted image (or original if already in target format)
        """
        # Normalize format names
        source_format = image.format.lower()
        if source_format == "jpg":
            source_format = "jpeg"

        # Skip SVG files - they can't be converted by PIL
        if source_format == "svg":
            return image

        # Skip if already in target format
        if source_format == self.target_format:
            return image

        # Load image
        img: PILImage = Image.open(BytesIO(image.data))

        # Handle transparency for JPEG (which doesn't support it)
        if self.target_format == "jpeg" and img.mode in ("RGBA", "LA", "P"):
            # Convert to RGB with white background
            if img.mode == "P":
                img = img.convert("RGBA")
            background: PILImage = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img)
            img = background

        # Convert CMYK to RGB if needed
        if img.mode == "CMYK":
            img = img.convert("RGB")

        # Save to target format
        output = BytesIO()
        save_kwargs = {}

        if self.target_format == "jpeg":
            save_kwargs["quality"] = 95
            save_kwargs["optimize"] = True
        elif self.target_format == "png":
            save_kwargs["optimize"] = True
        elif self.target_format == "webp":
            save_kwargs["quality"] = 95

        # Get PIL format name
        pil_format = self.target_format.upper()
        if pil_format == "JPG":
            pil_format = "JPEG"

        img.save(output, format=pil_format, **save_kwargs)

        # Create new filename with correct extension
        ext = "jpg" if self.target_format == "jpeg" else self.target_format
        base_name = image.filename.rsplit(".", 1)[0] if "." in image.filename else image.filename
        new_filename = f"{base_name}.{ext}"

        return ExtractedImage(
            filename=new_filename,
            data=output.getvalue(),
            format=self.target_format,
            page=image.page,
            caption=image.caption,
            context=image.context,
            description=image.description,
        )

    def convert_all(self, images: list[ExtractedImage]) -> list[ExtractedImage]:
        """Convert multiple images to the target format.

        Args:
            images: List of images to convert

        Returns:
            List of converted images
        """
        return [self.convert(img) for img in images]

    def should_convert(self, image: ExtractedImage) -> bool:
        """Check if an image needs conversion.

        Args:
            image: Image to check

        Returns:
            True if conversion is needed
        """
        source_format = image.format.lower()
        if source_format == "jpg":
            source_format = "jpeg"
        return source_format != self.target_format
