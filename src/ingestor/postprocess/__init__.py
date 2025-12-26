"""Post-processing utilities for extracted content."""

from .orphan_images import (
    detect_orphan_images,
    OrphanImageResult,
    recover_orphan_images,
    suggest_image_placements,
    smart_insert_images,
    find_figure_references,
    analyze_document_structure,
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
