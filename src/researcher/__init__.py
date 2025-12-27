"""Researcher module for programmatic deep research using Gemini API.

This module provides automated research capabilities using Google's
Gemini Deep Research Agent to conduct multi-step research tasks and
produce detailed, cited reports.

For parsing references from research output, use the parser module:
    from parser import ResearchParser, ParsedReference, ReferenceType
"""

from .deep_research import (
    DeepResearcher,
    ResearchConfig,
    ResearchResult,
    ResearchStatus,
)

__all__ = [
    "DeepResearcher",
    "ResearchResult",
    "ResearchConfig",
    "ResearchStatus",
]
