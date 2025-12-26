"""API clients for paper acquisition.

Provides clients for:
- Semantic Scholar: Paper search and metadata
- CrossRef: DOI resolution and metadata
- OpenAlex: Academic metadata and citations
- Unpaywall: Open access PDF locations
- arXiv: Preprint access and download
- PMC: PubMed Central biomedical literature
- bioRxiv/medRxiv: Biology and medical preprints
- Institutional: EZProxy and VPN access
- WebSearch: Claude Agent SDK web search for legal PDFs
- Sci-Hub: Unofficial PDF access (⚠️ legal concerns)
- LibGen: Unofficial PDF access (⚠️ legal concerns)
"""

from .base import BaseClient, RateLimiter
from .semantic_scholar import SemanticScholarClient
from .crossref import CrossRefClient
from .openalex import OpenAlexClient
from .unpaywall import UnpaywallClient
from .arxiv import ArxivClient
from .pmc import PMCClient
from .biorxiv import BioRxivClient
from .institutional import InstitutionalAccessClient
from .web_search import WebSearchClient
from .scihub import ScihubClient
from .libgen import LibGenClient

__all__ = [
    "BaseClient",
    "RateLimiter",
    "SemanticScholarClient",
    "CrossRefClient",
    "OpenAlexClient",
    "UnpaywallClient",
    "ArxivClient",
    "PMCClient",
    "BioRxivClient",
    "InstitutionalAccessClient",
    "WebSearchClient",
    "ScihubClient",
    "LibGenClient",
]
