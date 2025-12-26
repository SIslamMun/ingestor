"""Paper acquisition and extraction module.

Supports acquiring and processing scientific papers from:
- DOI strings (e.g., 10.1234/example)
- arXiv IDs (e.g., arXiv:2301.12345, 2301.12345)
- Semantic Scholar URLs/IDs
- OpenAlex IDs
- PubMed IDs
- Direct PDF URLs
- Paper titles (search-based)

Features:
- DOI resolution and paper download from multiple sources
- BibTeX/metadata extraction via CrossRef, Semantic Scholar, OpenAlex
- Citation and reference graph retrieval
- Open access PDF discovery via Unpaywall
- arXiv preprint download

Example:
    >>> from ingestor.extractors.paper import PaperExtractor, PaperConfig
    >>> config = PaperConfig(email="user@example.com")
    >>> extractor = PaperExtractor(config)
    >>> result = await extractor.extract("10.1038/nature12373")
    >>> print(result.markdown)
"""

from .paper_extractor import PaperExtractor, PaperConfig
from .resolver import PaperIdentifier, IdentifierType, resolve_identifier
from .metadata import PaperMetadata, Author, get_metadata
from .verifier import (
    CitationVerifier,
    BibEntry,
    VerificationResult,
    VerificationStats,
    parse_bib_file,
)

__all__ = [
    # Main extractor
    "PaperExtractor",
    "PaperConfig",
    # Identifier resolution
    "PaperIdentifier",
    "IdentifierType",
    "resolve_identifier",
    # Metadata
    "PaperMetadata",
    "Author",
    "get_metadata",
    # Citation verification
    "CitationVerifier",
    "BibEntry",
    "VerificationResult",
    "VerificationStats",
    "parse_bib_file",
]
