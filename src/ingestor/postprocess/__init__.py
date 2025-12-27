"""Post-processing utilities for extracted content."""

from .orphan_images import (
    OrphanImageResult,
    analyze_document_structure,
    detect_orphan_images,
    find_figure_references,
    recover_orphan_images,
    smart_insert_images,
    suggest_image_placements,
)

__all__ = [
    "detect_orphan_images",
    "OrphanImageResult",
    "recover_orphan_images",
    "suggest_image_placements",
    "smart_insert_images",
    "find_figure_references",
    "analyze_document_structure",
]
