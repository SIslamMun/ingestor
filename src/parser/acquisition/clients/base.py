"""Base client and rate limiting utilities."""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class RateLimiter:
    """Simple rate limiter for API calls.

    Args:
        calls_per_second: Maximum calls per second (can be fractional)
        min_delay: Minimum delay between calls in seconds
    """

    calls_per_second: float = 1.0
    min_delay: float = 0.1
    _last_call: float = field(default=0.0, repr=False)

    async def wait(self) -> None:
        """Wait if necessary to respect rate limit."""
        if self.calls_per_second <= 0:
            return

        delay = 1.0 / self.calls_per_second
        delay = max(delay, self.min_delay)

        now = time.monotonic()
        elapsed = now - self._last_call

        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)

        self._last_call = time.monotonic()


class BaseClient(ABC):
    """Base class for API clients."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        rate_limiter: RateLimiter | None = None,
    ):
        """Initialize the client.

        Args:
            base_url: Base URL for the API
            timeout: Request timeout in seconds
            rate_limiter: Rate limiter instance
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.rate_limiter = rate_limiter or RateLimiter()
        self._headers: dict[str, str] = {
            "User-Agent": "ingestor/1.0 (https://github.com/shazzadhk/ingestor)",
        }

    @property
    def headers(self) -> dict[str, str]:
        """Get request headers."""
        return self._headers.copy()

    def set_header(self, key: str, value: str) -> None:
        """Set a custom header."""
        self._headers[key] = value

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Make an HTTP request with rate limiting.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            json: JSON body
            **kwargs: Additional httpx request arguments

        Returns:
            JSON response or None if request failed
        """
        await self.rate_limiter.wait()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=self.headers,
                    **kwargs,
                )

                if response.status_code == 404:
                    return None

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError:
                return None
            except httpx.TimeoutException:
                return None
            except Exception:
                return None

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Make a GET request."""
        return await self._request("GET", endpoint, params=params, **kwargs)

    async def post(
        self,
        endpoint: str,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Make a POST request."""
        return await self._request("POST", endpoint, json=json, **kwargs)

    @abstractmethod
    async def get_paper_metadata(self, identifier: str) -> dict[str, Any] | None:
        """Get metadata for a paper by identifier.

        Args:
            identifier: Paper identifier (DOI, ID, etc.)

        Returns:
            Paper metadata dict or None
        """
        pass
