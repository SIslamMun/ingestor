"""bioRxiv/medRxiv API client for preprint access."""

from __future__ import annotations

from typing import Any, Optional

import httpx

from .base import BaseClient, RateLimiter


class BioRxivClient(BaseClient):
    """Client for bioRxiv and medRxiv APIs.
    
    Provides access to preprints from:
    - bioRxiv: Biology preprints
    - medRxiv: Medical/health sciences preprints
    
    Both share DOI prefix 10.1101.
    """

    BIORXIV_API = "https://api.biorxiv.org/details"
    MEDRXIV_API = "https://api.medrxiv.org/details"

    def __init__(self):
        """Initialize the bioRxiv client."""
        super().__init__(
            base_url="https://api.biorxiv.org",
            rate_limiter=RateLimiter(calls_per_second=2.0)
        )

    async def get_preprint(self, doi: str) -> Optional[dict[str, Any]]:
        """Get preprint metadata and PDF URL.

        Args:
            doi: The DOI to look up. Must start with 10.1101 for bioRxiv/medRxiv.

        Returns:
            Dict with preprint info and PDF URL, or None if not found.
        """
        # bioRxiv/medRxiv DOIs start with 10.1101
        if not doi.startswith("10.1101"):
            return None

        async with httpx.AsyncClient(timeout=30) as client:
            for server, api in [
                ("biorxiv", self.BIORXIV_API),
                ("medrxiv", self.MEDRXIV_API),
            ]:
                try:
                    url = f"{api}/{server}/{doi}/na/json"
                    response = await client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("collection"):
                            item = data["collection"][0]
                            return {
                                "title": item.get("title"),
                                "doi": doi,
                                "pdf_url": f"https://www.{server}.org/content/{doi}.full.pdf",
                                "server": server,
                                "authors": item.get("authors"),
                                "date": item.get("date"),
                                "category": item.get("category"),
                                "abstract": item.get("abstract"),
                            }
                except Exception:
                    continue

        return None

    async def get_pdf_url(self, doi: str) -> Optional[str]:
        """Get PDF URL for a bioRxiv/medRxiv DOI.

        Args:
            doi: The DOI to look up.

        Returns:
            PDF URL or None if not found.
        """
        result = await self.get_preprint(doi)
        if result:
            return result.get("pdf_url")
        return None

    async def search_by_date_range(
        self,
        server: str,
        start_date: str,
        end_date: str,
        cursor: int = 0,
    ) -> dict[str, Any]:
        """Search for preprints by date range.

        Args:
            server: Either 'biorxiv' or 'medrxiv'.
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.
            cursor: Pagination cursor.

        Returns:
            Dict with collection of results and message info.
        """
        base_url = self.BIORXIV_API if server == "biorxiv" else self.MEDRXIV_API
        url = f"{base_url}/{server}/{start_date}/{end_date}/{cursor}/json"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except Exception:
            return {"collection": [], "messages": []}

    async def search_by_title(
        self,
        title: str,
        server: str = "biorxiv",
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search preprints by title (approximate).
        
        Note: bioRxiv API doesn't have direct title search, so this
        searches recent preprints and filters by title similarity.
        For accurate title search, use CrossRef or Semantic Scholar.

        Args:
            title: Title to search for.
            server: 'biorxiv' or 'medrxiv'.
            max_results: Maximum results.

        Returns:
            List of matching preprints.
        """
        # bioRxiv API is limited - search recent dates
        # For real title search, recommend using CrossRef
        import datetime
        
        end_date = datetime.date.today().isoformat()
        start_date = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
        
        results = await self.search_by_date_range(server, start_date, end_date)
        
        # Filter by title similarity
        title_lower = title.lower()
        matches = []
        
        for item in results.get("collection", []):
            item_title = item.get("title", "").lower()
            # Simple substring match
            if title_lower in item_title or item_title in title_lower:
                matches.append({
                    "title": item.get("title"),
                    "doi": item.get("doi"),
                    "pdf_url": f"https://www.{server}.org/content/{item.get('doi')}.full.pdf",
                    "server": server,
                    "authors": item.get("authors"),
                    "date": item.get("date"),
                })
                if len(matches) >= max_results:
                    break
        
        return matches

    async def get_paper_metadata(self, identifier: str) -> Optional[dict[str, Any]]:
        """Get metadata for a paper by DOI.

        Args:
            identifier: The DOI (must start with 10.1101 for bioRxiv/medRxiv).

        Returns:
            Paper metadata dict or None.
        """
        return await self.get_preprint(identifier)
