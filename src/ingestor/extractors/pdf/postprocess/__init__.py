"""Deterministic post-processing for PDF-extracted markdown.

Ported from paper-to-md project for academic paper processing.
"""

from .bibliography import process_bibliography
from .citations import process_citations
from .cleanup import cleanup_text
from .equations import process_equations
from .figures import process_figures
from .sections import process_sections


def process_markdown(content: str, images: list[str] | None = None) -> str:
    """
    Apply all deterministic post-processing steps to markdown content.

    Args:
        content: Raw markdown content from extraction
        images: List of available image filenames (e.g., ["figure1.png", "figure2.png"])

    Returns:
        Processed markdown content
    """
    # Order matters: sections first, then citations, then equations, then figures, then bibliography
    content = process_sections(content)
    content = process_citations(content)
    content = process_equations(content)
    content = process_figures(content, images or [])
    content = process_bibliography(content)
    content = cleanup_text(content)
    return content


__all__ = [
    "process_markdown",
    "process_citations",
    "process_sections",
    "process_figures",
    "process_equations",
    "process_bibliography",
    "cleanup_text",
]
