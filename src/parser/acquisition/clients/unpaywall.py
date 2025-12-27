"""Unpaywall API client for open access PDF discovery."""

from __future__ import annotations

from typing import Any

from .base import BaseClient, RateLimiter


class UnpaywallClient(BaseClient):
    """Client for the Unpaywall API.

    See: https://unpaywall.org/products/api
    """

    BASE_URL = "https://api.unpaywall.org/v2"

    def __init__(self, email: str):
        """Initialize the Unpaywall client.

        Args:
            email: Email address (required for API access)
        """
        # Unpaywall: 100k/day = ~1/sec
        super().__init__(
            base_url=self.BASE_URL,
            rate_limiter=RateLimiter(calls_per_second=1.0),
        )

        if not email:
            raise ValueError("Email is required for Unpaywall API")

        self.email = email

    async def get_paper_metadata(self, identifier: str) -> dict[str, Any] | None:
        """Get paper metadata and open access info.

        Args:
            identifier: DOI

        Returns:
            Paper metadata dict with OA locations or None
        """
        # Clean DOI
        doi = identifier.strip()
        if doi.startswith("https://doi.org/"):
            doi = doi[16:]
        elif doi.startswith("http://dx.doi.org/"):
            doi = doi[18:]
        elif doi.lower().startswith("doi:"):
            doi = doi[4:]

        data = await self.get(doi, params={"email": self.email})

        if not data:
            return None

        # Get best OA location
        best_oa = data.get("best_oa_location", {}) or {}

        # Get all OA locations
        oa_locations = []
        for loc in data.get("oa_locations", []):
            oa_locations.append({
                "url": loc.get("url"),
                "pdf_url": loc.get("url_for_pdf"),
                "host_type": loc.get("host_type"),
                "license": loc.get("license"),
                "version": loc.get("version"),
                "is_best": loc == best_oa,
            })

        return {
            "title": data.get("title"),
            "doi": data.get("doi"),
            "year": data.get("year"),
            "publisher": data.get("publisher"),
            "journal": data.get("journal_name"),
            "is_open_access": data.get("is_oa"),
            "oa_status": data.get("oa_status"),
            "pdf_url": best_oa.get("url_for_pdf"),
            "landing_page": best_oa.get("url"),
            "host_type": best_oa.get("host_type"),
            "license": best_oa.get("license"),
            "version": best_oa.get("version"),
            "oa_locations": oa_locations,
            "source": "unpaywall",
        }

    async def get_pdf_url(self, doi: str) -> str | None:
        """Get the best open access PDF URL for a DOI.

        Args:
            doi: The DOI to look up

        Returns:
            PDF URL or None if not available
        """
        metadata = await self.get_paper_metadata(doi)

        if not metadata:
            return None

        # Try best OA location first
        if metadata.get("pdf_url"):
            return metadata["pdf_url"]

        # Try other locations
        for loc in metadata.get("oa_locations", []):
            if loc.get("pdf_url"):
                return loc["pdf_url"]

        return None

    async def get_all_pdf_urls(self, doi: str) -> list[dict[str, Any]]:
        """Get all available PDF URLs for a DOI.

        Args:
            doi: The DOI to look up

        Returns:
            List of location dicts with PDF URLs
        """
        metadata = await self.get_paper_metadata(doi)

        if not metadata:
            return []

        return [
            loc for loc in metadata.get("oa_locations", [])
            if loc.get("pdf_url")
        ]
