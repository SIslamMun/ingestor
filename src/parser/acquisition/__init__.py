"""acquisition - Paper acquisition module.

Multi-source PDF retrieval with fallback and rate limiting.
Based on: https://github.com/paper-acq/paper-retriever

Key Features:
- Multi-source PDF retrieval (Unpaywall, arXiv, PMC, S2, etc.)
- Configurable source priority
- Rate limiting per source
- Detailed logging per paper
- Batch retrieval with progress tracking
- API clients for various sources
"""

from .config import Config
from .downloader import (
    DownloadConfig,
    DownloadResult,
    PaperDownloader,
)
from .logger import RetrievalLogger
from .rate_limiter import RateLimiter
from .retriever import (
    PaperRetriever,
    RetrievalResult,
    RetrievalStatus,
)

__all__ = [
    # Retriever
    "PaperRetriever",
    "RetrievalResult",
    "RetrievalStatus",
    # Downloader
    "PaperDownloader",
    "DownloadConfig",
    "DownloadResult",
    # Logger
    "RetrievalLogger",
    # Config
    "Config",
    "RateLimiter",
]
