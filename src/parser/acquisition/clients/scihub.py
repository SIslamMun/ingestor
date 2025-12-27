"""Sci-Hub client for downloading papers.

⚠️ LEGAL WARNING ⚠️
Sci-Hub operates in a legal gray area in many jurisdictions.
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

import httpx


class ScihubClient:
    """Client for downloading papers from Sci-Hub.

    ⚠️ WARNING: Use may violate copyright laws. Disabled by default.

    Uses direct HTTP requests to Sci-Hub mirrors.
    Optionally uses scidownl library if installed.
    """

    # Known working Sci-Hub mirrors (community maintained)
    MIRRORS = [
        "https://sci-hub.se",
        "https://sci-hub.st",
        "https://sci-hub.ru",
    ]

    def __init__(
        self,
        enabled: bool = False,
        timeout: float = 60.0,
        max_retries: int = 2,
        rate_limit: float = 2.0,
    ):
        """Initialize the Sci-Hub client.

        Args:
            enabled: Must be True to use (disabled by default for legal reasons)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts per mirror
            rate_limit: Seconds between requests
        """
        self.enabled = enabled
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit = rate_limit
        self._last_request: float = 0.0
        self._scidownl_available = self._check_scidownl()

        if enabled:
            print("⚠️ WARNING: Sci-Hub client enabled. Use may violate copyright laws.")

    def _check_scidownl(self) -> bool:
        """Check if scidownl library is available."""
        try:
            from scidownl import scihub_download  # noqa: F401
            return True
        except ImportError:
            return False

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

        # Try scidownl first if available
        if self._scidownl_available:
            result = await self._download_with_scidownl(doi, "doi", output_path)
            if result:
                return result

        # Fallback to direct method
        return await self._download_direct(doi, output_path)

    async def download_by_title(
        self,
        title: str,
        output_path: Path,
    ) -> dict[str, Any] | None:
        """Download a paper by title (less reliable).

        Args:
            title: The paper title
            output_path: Path to save the PDF

        Returns:
            Dict with 'pdf_path' and 'source' if successful, None otherwise
        """
        if not self.enabled:
            return None

        await self._rate_limit_wait()

        if self._scidownl_available:
            return await self._download_with_scidownl(title, "title", output_path)

        return None  # Direct method only works with DOI

    async def _download_with_scidownl(
        self,
        identifier: str,
        paper_type: str,
        output_path: Path,
    ) -> dict[str, Any] | None:
        """Download using scidownl library.

        Args:
            identifier: DOI, PMID, or title
            paper_type: Type of identifier ("doi", "pmid", "title")
            output_path: Path to save the PDF

        Returns:
            Result dict or None
        """
        import logging
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO

        from scidownl import scihub_download

        try:
            loop = asyncio.get_event_loop()
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            def do_download():
                # Suppress verbose output
                captured_out = StringIO()
                captured_err = StringIO()

                try:
                    import loguru
                    loguru.logger.disable("scidownl")
                except ImportError:
                    pass

                logging.getLogger("scidownl").setLevel(logging.CRITICAL)

                try:
                    with redirect_stdout(captured_out), redirect_stderr(captured_err):
                        scihub_download(
                            identifier,
                            paper_type=paper_type,
                            out=str(output_path),
                        )
                except Exception:
                    pass

                return output_path.exists()

            success = await loop.run_in_executor(None, do_download)

            if success and output_path.exists():
                content = output_path.read_bytes()
                if content.startswith(b"%PDF") and len(content) > 1000:
                    return {"pdf_path": str(output_path), "source": "scihub"}
                else:
                    output_path.unlink(missing_ok=True)

        except Exception:
            pass

        return None

    async def _download_direct(
        self,
        doi: str,
        output_path: Path,
    ) -> dict[str, Any] | None:
        """Download directly from Sci-Hub mirrors.

        Args:
            doi: The DOI to download
            output_path: Path to save the PDF

        Returns:
            Result dict or None
        """
        for mirror in self.MIRRORS:
            for _attempt in range(self.max_retries):
                try:
                    result = await self._try_mirror(mirror, doi, output_path)
                    if result:
                        return result
                except Exception:
                    await asyncio.sleep(1)

        return None

    async def _try_mirror(
        self,
        mirror: str,
        doi: str,
        output_path: Path,
    ) -> dict[str, Any] | None:
        """Try to download from a specific mirror.

        Args:
            mirror: The Sci-Hub mirror URL
            doi: The DOI to download
            output_path: Path to save the PDF

        Returns:
            Result dict or None
        """
        url = f"{mirror}/{doi}"

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)

            if response.status_code in (503, 404):
                return None

            response.raise_for_status()

            # Extract PDF URL from page
            pdf_url = self._extract_pdf_url(response.text, mirror)
            if not pdf_url:
                return None

            # Download the PDF
            pdf_response = await client.get(pdf_url)
            pdf_response.raise_for_status()

            content = pdf_response.content
            if not content.startswith(b"%PDF") or len(content) < 1000:
                return None

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(content)

            return {"pdf_path": str(output_path), "source": "scihub"}

    def _extract_pdf_url(self, html: str, mirror: str) -> str | None:
        """Extract PDF URL from Sci-Hub page.

        Args:
            html: The HTML content
            mirror: The mirror base URL

        Returns:
            PDF URL or None
        """
        patterns = [
            r'<iframe[^>]+src="([^"]+\.pdf[^"]*)"',
            r'<embed[^>]+src="([^"]+\.pdf[^"]*)"',
            r'onclick="location\.href=\'([^\']+\.pdf[^\']*)\'"',
            r'<a[^>]+href="([^"]+\.pdf[^"]*)"[^>]*>',
            r'<iframe[^>]+src="([^"]+)"[^>]*id="pdf"',
            r'<embed[^>]+src="([^"]+)"[^>]*type="application/pdf"',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                pdf_url = match.group(1)
                if pdf_url.startswith("//"):
                    pdf_url = "https:" + pdf_url
                elif pdf_url.startswith("/"):
                    pdf_url = mirror + pdf_url
                return pdf_url

        return None

    def is_available(self) -> bool:
        """Check if the client is available and enabled.

        Returns:
            True if enabled
        """
        return self.enabled
