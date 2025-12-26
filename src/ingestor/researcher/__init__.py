"""Researcher module for programmatic deep research using Gemini API.

This module provides automated research capabilities using Google's
Gemini Deep Research Agent to conduct multi-step research tasks and
produce detailed, cited reports.
"""

from .deep_research import (
    DeepResearcher,
    ResearchResult,
    ResearchConfig,
    ResearchStatus,
)
from .parser import (
    ResearchParser,
    ParsedReference,
    ReferenceType,
)

__all__ = [
    "DeepResearcher",
    "ResearchResult", 
    "ResearchConfig",
    "ResearchStatus",
    "ResearchParser",
    "ParsedReference",
    "ReferenceType",
]
