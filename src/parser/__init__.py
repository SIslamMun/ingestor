"""Parser module - Paper acquisition and reference parsing.

Standalone module (separate from ingestor) for:
1. Downloading scientific papers
2. Parsing references from research documents

Supports acquiring papers from:
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
- Reference parsing from research documents

Example:
    >>> from parser import PaperDownloader, DownloadConfig
    >>> downloader = PaperDownloader()
    >>> result = await downloader.download("arXiv:2005.11401", output_dir="./papers")

    >>> from parser import ResearchParser
    >>> parser = ResearchParser()
    >>> refs = parser.parse_file("research_report.md")
"""

# Orchestration layer (from paper-acq)
from .acquisition.config import Config
from .acquisition.downloader import DownloadConfig, PaperDownloader
from .acquisition.logger import RetrievalLogger
from .acquisition.rate_limiter import RateLimiter
from .acquisition.retriever import PaperRetriever, RetrievalResult, RetrievalStatus
from .doi2bib.metadata import Author, PaperMetadata, get_metadata
from .doi2bib.resolver import IdentifierType, PaperIdentifier, resolve_identifier
from .doi2bib.verifier import (
    BibEntry,
    CitationVerifier,
    VerificationResult,
    VerificationStats,
    parse_bib_file,
)
from .parser import ParsedReference, ReferenceType, ResearchParser

__all__ = [
    # Main downloader
    "PaperDownloader",
    "DownloadConfig",
    # Identifier resolution
    "PaperIdentifier",
    "IdentifierType",
    "resolve_identifier",
    # Metadata
    "PaperMetadata",
    "Author",
    "get_metadata",
    # Parser
    "ResearchParser",
    "ParsedReference",
    "ReferenceType",
    # Citation verification
    "CitationVerifier",
    "BibEntry",
    "VerificationResult",
    "VerificationStats",
    "parse_bib_file",
    # Orchestration layer
    "Config",
    "RateLimiter",
    "RetrievalLogger",
    "PaperRetriever",
    "RetrievalResult",
    "RetrievalStatus",
]
