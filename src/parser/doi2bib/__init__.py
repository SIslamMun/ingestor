"""doi2bib - Citation verification and DOI resolution module.

Verifies BibTeX citations against CrossRef and arXiv APIs.
Based on: https://github.com/bibcure/doi2bib

Key Features:
- BibTeX file verification (single file or directory mode)
- DOI validation against CrossRef
- arXiv ID verification
- Website detection and access date handling
- Detailed reports (verified.bib, failed.bib, report.md)
- DOI/arXiv identifier resolution
- Metadata retrieval from CrossRef, Semantic Scholar, OpenAlex
"""

from .metadata import (
    Author,
    PaperMetadata,
    get_metadata,
)
from .resolver import (
    IdentifierType,
    PaperIdentifier,
    resolve_identifier,
)
from .verifier import (
    BibEntry,
    CitationVerifier,
    VerificationResult,
    VerificationStats,
    parse_bib_file,
)

__all__ = [
    # Verifier
    "CitationVerifier",
    "VerificationResult",
    "VerificationStats",
    "BibEntry",
    "parse_bib_file",
    # Resolver
    "PaperIdentifier",
    "IdentifierType",
    "resolve_identifier",
    # Metadata
    "PaperMetadata",
    "Author",
    "get_metadata",
]
