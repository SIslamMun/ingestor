"""Claude agent for markdown cleanup and enhancement."""

from typing import Any

from ...postprocess.orphan_images import (
    detect_orphan_images,
    smart_insert_images,
    suggest_image_placements,
)
from ...types import ExtractionResult


class ClaudeAgent:
    """Claude agent for cleaning up and enhancing extracted content.

    Uses the Claude Code SDK to process markdown output with
    intelligent cleanup, formatting, and restructuring.
    """

    DEFAULT_SYSTEM_PROMPT = """You are a markdown content editor. Your task is to clean up and enhance extracted markdown content while preserving all important information.

Guidelines:
1. Fix formatting issues (headers, lists, tables)
2. Remove extraction artifacts and noise
3. Improve readability and structure
4. Preserve all meaningful content
5. Maintain image references exactly as they are
6. Keep the document's original meaning and intent
7. Do not add new information or commentary"""

    def __init__(
        self,
        system_prompt: str | None = None,
    ):
        """Initialize Claude agent.

        Args:
            system_prompt: Custom system prompt for the agent
        """
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self._sdk: Any = None

    def _get_sdk(self) -> Any:
        """Get or create Claude SDK client."""
        if self._sdk is None:
            try:
                from claude_code_sdk import ClaudeCode
                self._sdk = ClaudeCode()
            except ImportError as e:
                raise ImportError(
                    "Claude Code SDK not installed. "
                    "Install with: pip install claude-code-sdk"
                ) from e
        return self._sdk

    async def cleanup(
        self,
        content: str,
        context: str | None = None,
    ) -> str:
        """Clean up markdown content using Claude.

        Args:
            content: Markdown content to clean
            context: Optional context about the content source

        Returns:
            Cleaned markdown content
        """
        sdk = self._get_sdk()

        prompt = "Clean up the following extracted markdown content:\n\n"
        if context:
            prompt += f"Context: {context}\n\n"
        prompt += f"```markdown\n{content}\n```\n\n"
        prompt += "Return only the cleaned markdown, no explanations."

        response = await sdk.query(
            prompt=prompt,
            system=self.system_prompt,
        )

        # Extract markdown from response
        cleaned = response.strip()

        # Remove markdown code block if present
        if cleaned.startswith("```markdown"):
            cleaned = cleaned[11:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        return cleaned.strip()

    async def cleanup_result(
        self,
        result: ExtractionResult,
    ) -> ExtractionResult:
        """Clean up an extraction result.

        Args:
            result: Extraction result to clean

        Returns:
            Result with cleaned markdown
        """
        context = f"Source: {result.source}, Type: {result.media_type.value if result.media_type else 'unknown'}"

        cleaned_markdown = await self.cleanup(
            result.markdown,
            context=context,
        )

        return ExtractionResult(
            markdown=cleaned_markdown,
            title=result.title,
            source=result.source,
            media_type=result.media_type,
            images=result.images,
            metadata=result.metadata,
            charset=result.charset,
        )

    async def summarize(
        self,
        content: str,
        max_length: int | None = None,
    ) -> str:
        """Generate a summary of the content.

        Args:
            content: Content to summarize
            max_length: Maximum summary length in words

        Returns:
            Summary text
        """
        sdk = self._get_sdk()

        prompt = "Summarize the following content"
        if max_length:
            prompt += f" in approximately {max_length} words"
        prompt += f":\n\n{content}"

        response = await sdk.query(
            prompt=prompt,
            system="You are a concise summarizer. Provide clear, accurate summaries.",
        )

        return response.strip()

    async def extract_key_points(
        self,
        content: str,
        max_points: int = 10,
    ) -> str:
        """Extract key points from content.

        Args:
            content: Content to analyze
            max_points: Maximum number of points

        Returns:
            Markdown list of key points
        """
        sdk = self._get_sdk()

        prompt = (
            f"Extract the {max_points} most important key points from "
            f"the following content. Format as a markdown bulleted list:\n\n{content}"
        )

        response = await sdk.query(
            prompt=prompt,
            system="You extract key information concisely and accurately.",
        )

        return response.strip()

    async def recover_orphan_images(
        self,
        markdown: str,
        image_filenames: list[str],
        image_dir: str = "./img",
        use_ai: bool = True,
    ) -> str:
        """Detect and recover orphan images in markdown.

        First detects images that were extracted but not referenced,
        then either uses Claude for intelligent placement or falls
        back to heuristic placement.

        Args:
            markdown: The markdown content
            image_filenames: List of extracted image filenames
            image_dir: Image directory path
            use_ai: If True, use Claude for intelligent placement

        Returns:
            Markdown with orphan images inserted
        """
        # Detect orphans
        result = detect_orphan_images(markdown, image_filenames, image_dir)

        if not result.has_orphans:
            return markdown

        if use_ai:
            try:
                # Use Claude for intelligent placement
                return await self._ai_place_images(
                    markdown, result.orphan_images, image_dir
                )
            except Exception:
                # Fall back to heuristic placement
                pass

        # Use smart heuristic placement
        return smart_insert_images(markdown, result.orphan_images, image_dir)

    async def _ai_place_images(
        self,
        markdown: str,
        orphan_images: list[str],
        image_dir: str = "./img",
    ) -> str:
        """Use Claude to intelligently place orphan images.

        Args:
            markdown: The markdown content
            orphan_images: List of orphan image filenames
            image_dir: Image directory path

        Returns:
            Markdown with images placed by Claude
        """
        sdk = self._get_sdk()

        prompt = suggest_image_placements(markdown, orphan_images)

        system = """You are an expert at document structure and image placement.
Your task is to insert image references into markdown at the most appropriate positions.
Consider:
1. Figure captions and references in the text
2. Section topics and content relevance
3. Natural reading flow
4. Original document structure clues

Return ONLY the complete modified markdown with images inserted.
Use format: ![Descriptive Alt Text](./img/filename.ext)"""

        response = await sdk.query(prompt=prompt, system=system)

        # Extract markdown from response
        cleaned = response.strip()
        if cleaned.startswith("```markdown"):
            cleaned = cleaned[11:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        return cleaned.strip()

    async def cleanup_result_with_images(
        self,
        result: ExtractionResult,
        recover_orphans: bool = True,
    ) -> ExtractionResult:
        """Clean up extraction result and recover orphan images.

        Enhanced version of cleanup_result that also handles
        orphan image detection and recovery.

        Args:
            result: Extraction result to process
            recover_orphans: Whether to detect and insert orphan images

        Returns:
            Processed result with cleaned markdown and recovered images
        """
        markdown = result.markdown
        context = f"Source: {result.source}, Type: {result.media_type.value if result.media_type else 'unknown'}"

        # First, recover orphan images if requested
        if recover_orphans and result.images:
            image_filenames = [img.filename for img in result.images]
            markdown = await self.recover_orphan_images(
                markdown, image_filenames, "./img", use_ai=True
            )

        # Then clean up the markdown
        cleaned_markdown = await self.cleanup(markdown, context=context)

        return ExtractionResult(
            markdown=cleaned_markdown,
            title=result.title,
            source=result.source,
            media_type=result.media_type,
            images=result.images,
            metadata=result.metadata,
            charset=result.charset,
        )


async def cleanup_markdown(
    content: str,
    context: str | None = None,
) -> str:
    """Convenience function to clean up markdown content.

    Args:
        content: Content to clean
        context: Optional context

    Returns:
        Cleaned content
    """
    agent = ClaudeAgent()
    return await agent.cleanup(content, context)


async def recover_orphan_images_with_ai(
    markdown: str,
    image_filenames: list[str],
    image_dir: str = "./img",
) -> str:
    """Convenience function to recover orphan images using Claude.

    Args:
        markdown: Markdown content
        image_filenames: List of extracted image filenames
        image_dir: Image directory path

    Returns:
        Markdown with orphan images inserted
    """
    agent = ClaudeAgent()
    return await agent.recover_orphan_images(
        markdown, image_filenames, image_dir, use_ai=True
    )
