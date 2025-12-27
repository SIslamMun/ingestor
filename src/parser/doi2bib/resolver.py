"""Paper identifier resolution.

Resolves various paper identifier formats to canonical DOIs:
- DOI strings: 10.1234/example
- arXiv IDs: arXiv:2301.12345 or 2301.12345
- Semantic Scholar IDs/URLs
- OpenAlex IDs
- Direct PDF URLs
- Paper titles (via search)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse


class IdentifierType(Enum):
    """Types of paper identifiers."""

    DOI = "doi"
    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    OPENALEX = "openalex"
    PUBMED = "pubmed"
    PMC = "pmc"
    PDF_URL = "pdf_url"
    TITLE = "title"
    UNKNOWN = "unknown"


@dataclass
class PaperIdentifier:
    """Resolved paper identifier."""

    original: str  # Original input string
    type: IdentifierType
    value: str  # Normalized identifier value
    doi: str | None = None  # Resolved DOI if available
    arxiv_id: str | None = None  # arXiv ID if applicable
    url: str | None = None  # Direct URL if available

    @property
    def has_doi(self) -> bool:
        """Check if DOI is available."""
        return self.doi is not None

    def __str__(self) -> str:
        if self.doi:
            return f"DOI:{self.doi}"
        elif self.arxiv_id:
            return f"arXiv:{self.arxiv_id}"
        return f"{self.type.value}:{self.value}"


# Regex patterns for identifier detection
DOI_PATTERN = re.compile(
    r"^(?:https?://(?:dx\.)?doi\.org/)?(?:doi:?)?"
    r"(10\.\d{4,}/[^\s]+)$",
    re.IGNORECASE
)

# arXiv patterns: arXiv:2301.12345, arxiv.org/abs/2301.12345, 2301.12345
ARXIV_PATTERN = re.compile(
    r"^(?:https?://arxiv\.org/(?:abs|pdf)/)?(?:arXiv:?)?"
    r"(\d{4}\.\d{4,5}(?:v\d+)?|\w+(?:-\w+)?/\d{7})$",
    re.IGNORECASE
)

# arXiv DOI pattern: 10.48550/arXiv.2301.12345
ARXIV_DOI_PATTERN = re.compile(
    r"^10\.48550/arXiv\.(\d{4}\.\d{4,5}(?:v\d+)?)$",
    re.IGNORECASE
)

# Semantic Scholar patterns
S2_URL_PATTERN = re.compile(
    r"^https?://(?:www\.)?semanticscholar\.org/paper/[^/]+/([a-f0-9]{40})$",
    re.IGNORECASE
)
S2_ID_PATTERN = re.compile(r"^[a-f0-9]{40}$", re.IGNORECASE)

# OpenAlex patterns
OPENALEX_PATTERN = re.compile(
    r"^(?:https?://openalex\.org/)?(W\d+)$",
    re.IGNORECASE
)

# PubMed patterns (both old ncbi.nlm.nih.gov/pubmed and new pubmed.ncbi.nlm.nih.gov)
PUBMED_PATTERN = re.compile(
    r"^(?:https?://(?:(?:www\.)?ncbi\.nlm\.nih\.gov/pubmed/|pubmed\.ncbi\.nlm\.nih\.gov/))?(?:PMID:?)?(\d{7,8})$",
    re.IGNORECASE
)

# PMC patterns
PMC_PATTERN = re.compile(
    r"^(?:https?://(?:www\.)?ncbi\.nlm\.nih\.gov/pmc/articles/)?(PMC\d+)$",
    re.IGNORECASE
)

# PDF URL pattern
PDF_URL_PATTERN = re.compile(
    r"^https?://.*\.pdf(?:\?.*)?$",
    re.IGNORECASE
)


def resolve_identifier(input_str: str) -> PaperIdentifier:
    """
    Resolve a paper identifier string to a PaperIdentifier.

    Args:
        input_str: DOI, arXiv ID, URL, or paper title

    Returns:
        PaperIdentifier with resolved type and values
    """
    input_str = input_str.strip()

    # Check arXiv DOI first (special case)
    match = ARXIV_DOI_PATTERN.match(input_str)
    if match:
        arxiv_id = match.group(1)
        return PaperIdentifier(
            original=input_str,
            type=IdentifierType.ARXIV,
            value=arxiv_id,
            doi=f"10.48550/arXiv.{arxiv_id}",
            arxiv_id=arxiv_id,
            url=f"https://arxiv.org/abs/{arxiv_id}",
        )

    # Check DOI
    match = DOI_PATTERN.match(input_str)
    if match:
        doi = match.group(1)
        return PaperIdentifier(
            original=input_str,
            type=IdentifierType.DOI,
            value=doi,
            doi=doi,
        )

    # Check arXiv ID/URL
    match = ARXIV_PATTERN.match(input_str)
    if match:
        arxiv_id = match.group(1)
        return PaperIdentifier(
            original=input_str,
            type=IdentifierType.ARXIV,
            value=arxiv_id,
            doi=f"10.48550/arXiv.{arxiv_id}",
            arxiv_id=arxiv_id,
            url=f"https://arxiv.org/abs/{arxiv_id}",
        )

    # Check Semantic Scholar URL
    match = S2_URL_PATTERN.match(input_str)
    if match:
        s2_id = match.group(1)
        return PaperIdentifier(
            original=input_str,
            type=IdentifierType.SEMANTIC_SCHOLAR,
            value=s2_id,
            url=input_str,
        )

    # Check Semantic Scholar ID (40-char hex)
    match = S2_ID_PATTERN.match(input_str)
    if match:
        return PaperIdentifier(
            original=input_str,
            type=IdentifierType.SEMANTIC_SCHOLAR,
            value=input_str.lower(),
            url=f"https://www.semanticscholar.org/paper/{input_str}",
        )

    # Check OpenAlex
    match = OPENALEX_PATTERN.match(input_str)
    if match:
        openalex_id = match.group(1).upper()
        return PaperIdentifier(
            original=input_str,
            type=IdentifierType.OPENALEX,
            value=openalex_id,
            url=f"https://openalex.org/{openalex_id}",
        )

    # Check PubMed
    match = PUBMED_PATTERN.match(input_str)
    if match:
        pmid = match.group(1)
        return PaperIdentifier(
            original=input_str,
            type=IdentifierType.PUBMED,
            value=pmid,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}",
        )

    # Check PMC
    match = PMC_PATTERN.match(input_str)
    if match:
        pmc_id = match.group(1).upper()
        return PaperIdentifier(
            original=input_str,
            type=IdentifierType.PMC,
            value=pmc_id,
            url=f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}",
        )

    # Check direct PDF URL
    if PDF_URL_PATTERN.match(input_str):
        return PaperIdentifier(
            original=input_str,
            type=IdentifierType.PDF_URL,
            value=input_str,
            url=input_str,
        )

    # Check if it's any URL (try to extract DOI from it)
    parsed = urlparse(input_str)
    if parsed.scheme in ("http", "https"):
        # Try to extract DOI from URL path
        path = parsed.path
        doi_in_path = re.search(r"(10\.\d{4,}/[^\s?#]+)", path)
        if doi_in_path:
            doi = doi_in_path.group(1)
            return PaperIdentifier(
                original=input_str,
                type=IdentifierType.DOI,
                value=doi,
                doi=doi,
                url=input_str,
            )

        # Unknown URL, treat as PDF URL if we can't identify it
        return PaperIdentifier(
            original=input_str,
            type=IdentifierType.PDF_URL,
            value=input_str,
            url=input_str,
        )

    # Assume it's a title search
    return PaperIdentifier(
        original=input_str,
        type=IdentifierType.TITLE,
        value=input_str,
    )


def normalize_doi(doi: str) -> str:
    """Normalize a DOI string."""
    # Remove URL prefixes
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi:?", "", doi, flags=re.IGNORECASE)
    return doi.strip()


def normalize_arxiv_id(arxiv_id: str) -> str:
    """Normalize an arXiv ID."""
    # Remove URL prefixes
    arxiv_id = re.sub(r"^https?://arxiv\.org/(?:abs|pdf)/", "", arxiv_id, flags=re.IGNORECASE)
    arxiv_id = re.sub(r"^arXiv:?", "", arxiv_id, flags=re.IGNORECASE)
    # Remove .pdf suffix
    arxiv_id = re.sub(r"\.pdf$", "", arxiv_id, flags=re.IGNORECASE)
    return arxiv_id.strip()


def arxiv_id_to_doi(arxiv_id: str) -> str:
    """Convert arXiv ID to DOI format."""
    arxiv_id = normalize_arxiv_id(arxiv_id)
    return f"10.48550/arXiv.{arxiv_id}"
