"""Orphan image detection and recovery utilities.

Detects images that are extracted but not referenced in markdown,
and provides utilities to insert references at appropriate positions.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class OrphanImageResult:
    """Result of orphan image detection."""

    orphan_images: list[str]  # Images not referenced in markdown
    referenced_images: list[str]  # Images that are referenced
    missing_images: list[str]  # References to images that don't exist
    total_images: int
    total_references: int

    @property
    def has_orphans(self) -> bool:
        """Check if there are any orphan images."""
        return len(self.orphan_images) > 0

    @property
    def has_missing(self) -> bool:
        """Check if there are references to missing images."""
        return len(self.missing_images) > 0

    def summary(self) -> str:
        """Generate a summary of the orphan image analysis."""
        lines = [
            f"Total images: {self.total_images}",
            f"Total references: {self.total_references}",
            f"Referenced: {len(self.referenced_images)}",
            f"Orphaned: {len(self.orphan_images)}",
            f"Missing: {len(self.missing_images)}",
        ]
        if self.orphan_images:
            lines.append("\nOrphan images (not referenced):")
            for img in self.orphan_images:
                lines.append(f"  - {img}")
        if self.missing_images:
            lines.append("\nMissing images (referenced but not found):")
            for img in self.missing_images:
                lines.append(f"  - {img}")
        return "\n".join(lines)


def detect_orphan_images(
    markdown: str,
    image_filenames: list[str],
    image_dir: str = "./img",
) -> OrphanImageResult:
    """Detect orphan images that are not referenced in markdown.

    Args:
        markdown: The markdown content to analyze
        image_filenames: List of image filenames that were extracted
        image_dir: The image directory path used in references (default: ./img)

    Returns:
        OrphanImageResult with analysis of image references
    """
    # Find all image references in markdown
    # Patterns: ![alt](path) or ![](path)
    image_ref_pattern = r"!\[[^\]]*\]\(([^)]+)\)"
    references = re.findall(image_ref_pattern, markdown)

    # Normalize references - extract just the filename
    referenced_files = set()
    for ref in references:
        # Handle both ./img/name.png and just name.png
        ref_path = Path(ref)
        referenced_files.add(ref_path.name)

    # Convert image_filenames to a set for faster lookup
    available_images = set(image_filenames)

    # Find orphans (extracted but not referenced)
    orphan_images = [img for img in image_filenames if img not in referenced_files]

    # Find referenced images
    referenced_images = [img for img in image_filenames if img in referenced_files]

    # Find missing images (referenced but not in available)
    missing_images = [ref for ref in referenced_files if ref not in available_images]

    return OrphanImageResult(
        orphan_images=orphan_images,
        referenced_images=referenced_images,
        missing_images=missing_images,
        total_images=len(image_filenames),
        total_references=len(references),
    )


def recover_orphan_images(
    markdown: str,
    orphan_images: list[str],
    image_dir: str = "./img",
    position: str = "end",
    section_title: Optional[str] = "Images",
) -> str:
    """Insert orphan images into markdown at specified position.

    This is a simple deterministic recovery that appends images
    at the end or under a section. For intelligent placement,
    use suggest_image_placements with Claude.

    Args:
        markdown: The markdown content
        orphan_images: List of orphan image filenames to insert
        image_dir: Directory path for image references
        position: Where to insert - "end" or "section"
        section_title: Title for the images section (if position="section")

    Returns:
        Markdown with orphan images inserted
    """
    if not orphan_images:
        return markdown

    # Generate image references
    image_refs = []
    for i, img in enumerate(orphan_images, 1):
        # Try to generate a meaningful alt text from filename
        alt_text = _generate_alt_text(img)
        ref = f"![{alt_text}]({image_dir}/{img})"
        image_refs.append(ref)

    # Insert based on position
    if position == "end":
        # Simply append at the end
        images_block = "\n\n---\n\n## Additional Images\n\n"
        images_block += "\n\n".join(image_refs)
        return markdown.rstrip() + images_block + "\n"

    elif position == "section":
        # Add as a dedicated section
        images_block = f"\n\n## {section_title}\n\n"
        images_block += "\n\n".join(image_refs)
        return markdown.rstrip() + images_block + "\n"

    return markdown


def _generate_alt_text(filename: str) -> str:
    """Generate alt text from filename.

    Args:
        filename: Image filename

    Returns:
        Human-readable alt text
    """
    # Remove extension
    name = Path(filename).stem

    # Common patterns to clean up
    # figure_001 -> Figure 1
    # slide3_img2 -> Slide 3 Image 2
    # image_1_9cd53a2f -> Image 1

    # Remove hash suffixes (like _9cd53a2f)
    name = re.sub(r"_[a-f0-9]{6,}$", "", name)

    # Replace underscores with spaces
    name = name.replace("_", " ")

    # Capitalize words
    words = name.split()
    capitalized = []
    for word in words:
        # Handle numbers - "001" -> "1"
        if word.isdigit():
            capitalized.append(str(int(word)))
        else:
            capitalized.append(word.capitalize())

    return " ".join(capitalized) if capitalized else "Image"


def suggest_image_placements(
    markdown: str,
    orphan_images: list[str],
    image_contexts: Optional[dict[str, str]] = None,
) -> str:
    """Generate a prompt for Claude to suggest image placements.

    This creates a structured prompt that can be sent to Claude
    for intelligent image placement suggestions.

    Args:
        markdown: The markdown content
        orphan_images: List of orphan image filenames
        image_contexts: Optional dict mapping filename to context/caption

    Returns:
        Prompt string for Claude
    """
    prompt_parts = [
        "Analyze this markdown document and suggest where to insert the following orphan images.",
        "For each image, identify the most appropriate location based on:",
        "1. Figure/image captions or references in the text",
        "2. Context clues (e.g., 'as shown in Figure 1')",
        "3. Logical document structure",
        "",
        "## Document Content",
        "```markdown",
        markdown,
        "```",
        "",
        "## Orphan Images to Place",
    ]

    for img in orphan_images:
        prompt_parts.append(f"- `{img}`")
        if image_contexts and img in image_contexts:
            prompt_parts.append(f"  Context: {image_contexts[img]}")

    prompt_parts.extend([
        "",
        "## Instructions",
        "Return the complete markdown with images inserted at appropriate positions.",
        "Use the format: ![Descriptive alt text](./img/filename.ext)",
        "If you cannot determine a good position, place the image after the most relevant section.",
        "Only return the modified markdown, no explanations.",
    ])

    return "\n".join(prompt_parts)


def find_figure_references(markdown: str) -> list[tuple[str, int, int]]:
    """Find text references to figures/images in markdown.

    Looks for patterns like:
    - "Figure 1", "Fig. 1", "Figure 1a"
    - "see figure below", "as shown above"
    - "diagram", "chart", "screenshot", "photo"

    Args:
        markdown: Markdown content to analyze

    Returns:
        List of (match_text, start_pos, end_pos) tuples
    """
    patterns = [
        # Explicit figure references
        r"[Ff]ig(?:ure)?\.?\s*\d+[a-zA-Z]?",
        r"[Ii]mage\s*\d+",
        r"[Dd]iagram\s*\d+",
        r"[Cc]hart\s*\d+",
        r"[Tt]able\s*\d+",
        r"[Pp]late\s*\d+",
        # Directional references
        r"(?:as\s+)?(?:shown|displayed|illustrated)\s+(?:in\s+)?(?:the\s+)?(?:figure|image|diagram)\s+(?:below|above)",
        r"see\s+(?:the\s+)?(?:figure|image|diagram)\s+(?:below|above)",
        # Generic mentions that might indicate an image should be nearby
        r"the\s+following\s+(?:figure|image|diagram|chart|screenshot)",
    ]

    results = []
    for pattern in patterns:
        for match in re.finditer(pattern, markdown, re.IGNORECASE):
            results.append((match.group(), match.start(), match.end()))

    # Sort by position
    results.sort(key=lambda x: x[1])
    return results


def analyze_document_structure(markdown: str) -> dict:
    """Analyze document structure to help with image placement.

    Args:
        markdown: Markdown content

    Returns:
        Dict with structure analysis:
        - sections: list of (heading_text, level, position)
        - figure_refs: list of figure references found
        - paragraphs: list of (text, start, end) for each paragraph
    """
    # Find all headings
    heading_pattern = r"^(#{1,6})\s+(.+)$"
    sections = []
    for match in re.finditer(heading_pattern, markdown, re.MULTILINE):
        level = len(match.group(1))
        text = match.group(2)
        sections.append((text, level, match.start()))

    # Find figure references
    figure_refs = find_figure_references(markdown)

    # Find paragraphs (blocks of text between blank lines)
    paragraphs = []
    para_pattern = r"(?:^|\n\n)([^\n#*\-|].+?)(?=\n\n|$)"
    for match in re.finditer(para_pattern, markdown, re.DOTALL):
        text = match.group(1).strip()
        if text and len(text) > 20:  # Skip very short paragraphs
            paragraphs.append((text[:100] + "..." if len(text) > 100 else text,
                              match.start(), match.end()))

    return {
        "sections": sections,
        "figure_refs": figure_refs,
        "paragraphs": paragraphs,
    }


def smart_insert_images(
    markdown: str,
    orphan_images: list[str],
    image_dir: str = "./img",
) -> str:
    """Attempt to intelligently insert orphan images based on document analysis.

    This is a heuristic approach that:
    1. Looks for figure references (Fig. 1, Figure 2, etc.)
    2. Matches images by number if possible
    3. Places remaining images at section boundaries

    For best results with complex documents, use Claude agent.

    Args:
        markdown: Markdown content
        orphan_images: List of orphan image filenames
        image_dir: Image directory path

    Returns:
        Markdown with images inserted
    """
    if not orphan_images:
        return markdown

    # Analyze document structure
    structure = analyze_document_structure(markdown)
    figure_refs = structure["figure_refs"]

    # Try to match images to figure references by number
    placed_images = set()
    insertions = []  # (position, image_ref)

    for img in orphan_images:
        # Extract number from image filename
        img_num_match = re.search(r"(\d+)", img)
        if img_num_match:
            img_num = img_num_match.group(1)

            # Look for matching figure reference
            for ref_text, ref_start, ref_end in figure_refs:
                ref_num_match = re.search(r"\d+", ref_text)
                if ref_num_match and ref_num_match.group() == img_num:
                    # Found a match! Insert after this reference
                    alt_text = _generate_alt_text(img)
                    image_ref = f"\n\n![{alt_text}]({image_dir}/{img})\n"

                    # Find the end of the paragraph containing this reference
                    para_end = markdown.find("\n\n", ref_end)
                    if para_end == -1:
                        para_end = len(markdown)

                    insertions.append((para_end, image_ref))
                    placed_images.add(img)
                    break

    # Apply insertions in reverse order to preserve positions
    result = markdown
    for pos, ref in sorted(insertions, reverse=True):
        result = result[:pos] + ref + result[pos:]

    # Handle remaining orphans - append at end
    remaining = [img for img in orphan_images if img not in placed_images]
    if remaining:
        result = recover_orphan_images(result, remaining, image_dir, position="end")

    return result
