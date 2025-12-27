"""Library Genesis client for downloading academic papers.

⚠️ LEGAL WARNING ⚠️
Library Genesis operates in a legal gray area in many jurisdictions.
Use of this client may violate copyright laws in your country.
This client is provided for educational and research purposes only.
Users are responsible for ensuring their use complies with local laws.

The client is disabled by default and must be explicitly enabled.
"""

from __future__ import annotations

import asyncio
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx


class LibGenClient:
    """Client for downloading papers from Library Genesis.

    ⚠️ WARNING: Use may violate copyright laws. Disabled by default.

    Uses direct HTTP requests to search and download from scimag (scientific articles).
    """

    # LibGen mirrors for scientific articles (scimag)
    SEARCH_MIRRORS = [
        "https://libgen.rs/scimag/",
        "https://libgen.is/scimag/",
        "https://libgen.st/scimag/",
    ]

    DOWNLOAD_MIRRORS = [
        "https://libgen.rs",
        "https://libgen.is",
        "https://library.lol",
    ]

    def __init__(
        self,
        enabled: bool = False,
        timeout: float = 60.0,
        max_retries: int = 2,
        rate_limit: float = 2.0,
    ):
        """Initialize the LibGen client.

        Args:
            enabled: Must be True to use (disabled by default for legal reasons)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            rate_limit: Seconds between requests
        """
        self.enabled = enabled
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit = rate_limit
        self._last_request: float = 0.0

        if enabled:
            print("⚠️ WARNING: LibGen client enabled. Use may violate copyright laws.")

    async def _rate_limit_wait(self) -> None:
        """Wait to respect rate limits."""
        now = time.time()
        elapsed = now - self._last_request
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        self._last_request = time.time()

    async def download_by_doi(
        self,
        doi: str,
        output_path: Path,
    ) -> dict[str, Any] | None:
        """Download a paper by DOI.

        Args:
            doi: The DOI of the paper
            output_path: Path to save the PDF

        Returns:
            Dict with 'pdf_path' and 'source' if successful, None otherwise
        """
        if not self.enabled:
            return None

        await self._rate_limit_wait()
        output_path = Path(output_path)

        for mirror in self.SEARCH_MIRRORS:
            try:
                result = await self._search_and_download(
                    mirror, doi, output_path, search_type="doi"
                )
                if result:
                    return result
            except Exception:
                continue

        return None

    async def download_by_title(
        self,
        title: str,
        output_path: Path,
    ) -> dict[str, Any] | None:
        """Download a paper by title.

        Args:
            title: The paper title
            output_path: Path to save the PDF

        Returns:
            Dict with 'pdf_path' and 'source' if successful, None otherwise
        """
        if not self.enabled:
            return None

        await self._rate_limit_wait()
        output_path = Path(output_path)

        for mirror in self.SEARCH_MIRRORS:
            try:
                result = await self._search_and_download(
                    mirror, title, output_path, search_type="title"
                )
                if result:
                    return result
            except Exception:
                continue

        return None

    async def _search_and_download(
        self,
        mirror: str,
        query: str,
        output_path: Path,
        search_type: str = "doi",
    ) -> dict[str, Any] | None:
        """Search LibGen and download the first matching result.

        Args:
            mirror: LibGen mirror URL
            query: Search query (DOI or title)
            output_path: Path to save the PDF
            search_type: Type of search ("doi" or "title")

        Returns:
            Result dict or None
        """
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            # Search for the paper
            encoded_query = quote_plus(query)
            search_url = f"{mirror}?q={encoded_query}"

            for attempt in range(self.max_retries):
                try:
                    response = await client.get(search_url)

                    if response.status_code == 503:
                        await asyncio.sleep(2)
                        continue

                    response.raise_for_status()
                    break
                except httpx.HTTPStatusError:
                    if attempt == self.max_retries - 1:
                        return None
                    await asyncio.sleep(1)
            else:
                return None

            # Parse the search results to find download links
            download_info = self._extract_download_info(response.text)
            if not download_info:
                return None

            # Try to get the PDF
            pdf_url = await self._resolve_download_link(client, download_info)
            if not pdf_url:
                return None

            # Download the PDF
            return await self._download_pdf(client, pdf_url, output_path)

    def _extract_download_info(self, html: str) -> dict[str, str] | None:
        """Extract download page URL or direct link from search results.

        Args:
            html: The HTML content of search results

        Returns:
            Dict with download info or None
        """
        patterns = [
            # Direct get.php links
            (r'href="(https?://[^"]*get\.php\?md5=[^"]+)"', "get_php"),
            # Library.lol links
            (r'href="(https?://library\.lol/[^"]+)"', "library_lol"),
            # Relative get.php links
            (r'href="(/scimag/get\.php\?md5=[^"]+)"', "relative_get"),
            # DOI.org links
            (r'href="(https?://doi\.org/[^"]+)"', "doi_link"),
        ]

        for pattern, link_type in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return {"url": match.group(1), "type": link_type}

        # Also look for any GET button/link
        get_pattern = r'<a[^>]+href="([^"]+)"[^>]*>\s*GET\s*</a>'
        match = re.search(get_pattern, html, re.IGNORECASE)
        if match:
            return {"url": match.group(1), "type": "get_button"}

        return None

    async def _resolve_download_link(
        self,
        client: httpx.AsyncClient,
        download_info: dict[str, str],
    ) -> str | None:
        """Resolve a download page to get direct PDF link.

        Args:
            client: HTTP client
            download_info: Dict with 'url' and 'type'

        Returns:
            Direct PDF URL or None
        """
        url = download_info["url"]
        link_type = download_info["type"]

        # If it's a relative URL, try each download mirror
        if url.startswith("/"):
            for mirror in self.DOWNLOAD_MIRRORS:
                try:
                    full_url = mirror + url
                    response = await client.get(full_url)
                    response.raise_for_status()
                    pdf_url = self._extract_pdf_from_download_page(response.text)
                    if pdf_url:
                        return pdf_url
                except Exception:
                    continue
            return None

        # For library.lol or other full URLs
        if link_type in ("library_lol", "get_php", "get_button"):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return self._extract_pdf_from_download_page(response.text)
            except Exception:
                return None

        return None

    def _extract_pdf_from_download_page(self, html: str) -> str | None:
        """Extract direct PDF URL from download page.

        Args:
            html: The HTML content of download page

        Returns:
            Direct PDF URL or None
        """
        patterns = [
            # Direct PDF links
            r'href="(https?://[^"]+\.pdf)"',
            # Cloudflare/CDN download links
            r'href="(https?://download\.[^"]+)"',
            # GET button with direct link
            r'<a[^>]+href="([^"]+)"[^>]*>GET</a>',
            # Any download link
            r'<a[^>]+href="([^"]+)"[^>]*>\s*(?:Download|GET|PDF)\s*</a>',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                url = match.group(1)
                if not url.startswith("javascript:") and not url.startswith("#"):
                    return url

        return None

    async def _download_pdf(
        self,
        client: httpx.AsyncClient,
        pdf_url: str,
        output_path: Path,
    ) -> dict[str, Any] | None:
        """Download PDF from direct URL.

        Args:
            client: HTTP client
            pdf_url: Direct PDF URL
            output_path: Path to save the PDF

        Returns:
            Result dict or None
        """
        try:
            response = await client.get(pdf_url)
            response.raise_for_status()

            content = response.content
            if not content.startswith(b"%PDF") or len(content) < 1000:
                return None

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(content)

            return {"pdf_path": str(output_path), "source": "libgen"}

        except Exception:
            return None

    def is_available(self) -> bool:
        """Check if the client is available and enabled.

        Returns:
            True if enabled
        """
        return self.enabled
