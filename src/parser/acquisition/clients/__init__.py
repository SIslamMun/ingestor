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

from .arxiv import ArxivClient
from .base import BaseClient, RateLimiter
from .biorxiv import BioRxivClient
from .crossref import CrossRefClient
from .institutional import InstitutionalAccessClient
from .libgen import LibGenClient
from .openalex import OpenAlexClient
from .pmc import PMCClient
from .scihub import ScihubClient
from .semantic_scholar import SemanticScholarClient
from .unpaywall import UnpaywallClient
from .web_search import WebSearchClient

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
