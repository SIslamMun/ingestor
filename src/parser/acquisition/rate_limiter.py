"""Rate limiting utilities for API calls."""

import asyncio
import time
from typing import Any


class RateLimiter:
    """Global rate limiter for API calls across all sources.

    Ensures we don't exceed rate limits for any API by tracking
    the last call time per source and waiting if needed.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the rate limiter.

        Args:
            config: Rate limit configuration with 'per_source_delays' and 'global_delay'.
        """
        config = config or {}
        self.delays = config.get("per_source_delays", {
            "crossref": 0.5,
            "unpaywall": 0.1,
            "arxiv": 3.0,
            "pmc": 0.34,
            "semantic_scholar": 3.0,
            "openalex": 0.1,
            "biorxiv": 1.0,
            "scihub": 5.0,
            "libgen": 3.0,
        })
        self.global_delay = config.get("global_delay", 1.0)
        self.last_call: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def wait(self, source: str) -> None:
        """Wait appropriate time before next call to a source.

        Args:
            source: The source identifier to rate limit.
        """
        async with self._lock:
            delay = self.delays.get(source, self.global_delay)
            last = self.last_call.get(source, 0)
            elapsed = time.time() - last

            if elapsed < delay:
                await asyncio.sleep(delay - elapsed)

            self.last_call[source] = time.time()

    def wait_sync(self, source: str) -> None:
        """Synchronous version of wait.

        Args:
            source: The source identifier to rate limit.
        """
        delay = self.delays.get(source, self.global_delay)
        last = self.last_call.get(source, 0)
        elapsed = time.time() - last

        if elapsed < delay:
            time.sleep(delay - elapsed)

        self.last_call[source] = time.time()

    def get_delay(self, source: str) -> float:
        """Get the delay for a specific source.

        Args:
            source: The source identifier.

        Returns:
            The delay in seconds.
        """
        return self.delays.get(source, self.global_delay)

    def set_delay(self, source: str, delay: float) -> None:
        """Set the delay for a specific source.

        Args:
            source: The source identifier.
            delay: The delay in seconds.
        """
        self.delays[source] = delay
