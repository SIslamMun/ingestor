"""Web search fallback using Claude Agent SDK.

Searches for legal, freely accessible copies of papers on:
- Author's personal/academic websites
- Institutional repositories
- ResearchGate or Academia.edu
- Conference proceedings websites
- Preprint servers (arXiv, SSRN, etc.)

NOTE: This client intentionally does NOT search for or suggest:
- Sci-Hub or Library Genesis (legal concerns)
- Paid access or subscription links
- Links that require login
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any


class WebSearchClient:
    """Client for searching the web for paper PDFs using Claude Agent SDK.

    This is a fallback option when other sources don't have the paper.
    Uses Claude's web search capabilities to find author websites,
    institutional repositories, or other legal sources.
    """

    def __init__(
        self,
        enabled: bool = True,
        rate_limit: float = 2.0,
    ):
        """Initialize the web search client.

        Args:
            enabled: Whether web search is enabled
            rate_limit: Seconds between requests
        """
        self.enabled = enabled
        self.rate_limit = rate_limit
        self._sdk_available: bool | None = None
        self._last_request: float = 0.0

    async def _rate_limit_wait(self) -> None:
        """Wait to respect rate limits."""
        now = time.time()
        elapsed = now - self._last_request
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        self._last_request = time.time()

    def _check_sdk_available(self) -> bool:
        """Check if Claude Agent SDK is available."""
        if self._sdk_available is not None:
            return self._sdk_available

        try:
            from claude_code_sdk import query  # noqa: F401
            self._sdk_available = True
        except ImportError:
            self._sdk_available = False

        return self._sdk_available

    async def search_for_pdf(
        self,
        title: str,
        doi: str | None = None,
        authors: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Search the web for a PDF of the paper.

        Uses Claude Agent SDK to intelligently search for:
        - Author's personal/academic websites
        - Institutional repositories
        - ResearchGate or Academia.edu
        - Conference proceedings websites
        - Preprint servers

        Args:
            title: Paper title
            doi: Optional DOI
            authors: Optional list of author names

        Returns:
            Dict with 'pdf_url' and 'source' if found, None otherwise
        """
        if not self.enabled:
            return None

        if not self._check_sdk_available():
            return None

        await self._rate_limit_wait()

        from claude_code_sdk import ClaudeCodeOptions, query

        # Build search prompt
        author_str = ", ".join(authors[:3]) if authors else "Unknown authors"
        doi_line = f"DOI: {doi}" if doi else ""

        search_prompt = f"""Find a freely accessible PDF for this academic paper:

Title: {title}
{doi_line}
Authors: {author_str}

Search for legal, freely accessible copies on:
1. Author's personal or academic institution website
2. Institutional repositories (university archives)
3. ResearchGate or Academia.edu (public copies)
4. Conference proceedings websites
5. Preprint servers (arXiv, SSRN, etc.)

IMPORTANT: Only find legal, freely accessible copies. Do NOT suggest:
- Sci-Hub or Library Genesis
- Paid access or subscription links
- Links that require login

If you find a direct PDF link, return ONLY the URL on a single line.
If you cannot find a free legal copy, respond with: NOT_FOUND"""

        try:
            result = await query(
                prompt=search_prompt,
                options=ClaudeCodeOptions(
                    allowed_tools=["WebSearch", "WebFetch"],
                    permission_mode="auto",
                    max_turns=5,
                ),
            )

            # Process the result
            response_text = ""
            for message in result:
                if hasattr(message, "content"):
                    if isinstance(message.content, str):
                        response_text += message.content
                    elif isinstance(message.content, list):
                        for block in message.content:
                            if hasattr(block, "text"):
                                response_text += block.text

            # Extract PDF URL from response
            if "NOT_FOUND" in response_text.upper():
                return None

            # Look for PDF URLs in the response
            pdf_urls = re.findall(
                r"https?://[^\s<>\"']+\.pdf(?:\?[^\s<>\"']*)?",
                response_text,
                re.IGNORECASE,
            )

            if pdf_urls:
                return {"pdf_url": pdf_urls[0], "source": "web_search"}

            # Also look for URLs that might be PDF downloads
            all_urls = re.findall(r"https?://[^\s<>\"']+", response_text)
            for url in all_urls:
                if any(
                    x in url.lower()
                    for x in ["download", "pdf", "fulltext", "full-text"]
                ):
                    return {"pdf_url": url, "source": "web_search"}

            return None

        except Exception as e:
            print(f"Web search failed: {e}")
            return None

    async def search_author_page(
        self,
        author_name: str,
        paper_title: str,
    ) -> str | None:
        """Search for a paper on an author's academic webpage.

        Args:
            author_name: Author's name
            paper_title: Paper title to find

        Returns:
            PDF URL if found, None otherwise
        """
        if not self.enabled or not self._check_sdk_available():
            return None

        await self._rate_limit_wait()

        from claude_code_sdk import ClaudeCodeOptions, query

        search_prompt = f"""Find the academic webpage of {author_name} and look for a PDF of:
"{paper_title}"

Search for:
1. The author's university/institution webpage
2. Their personal academic website
3. Their Google Scholar or DBLP profile

If you find a direct PDF link to this paper, return ONLY the URL.
If not found, respond with: NOT_FOUND"""

        try:
            result = await query(
                prompt=search_prompt,
                options=ClaudeCodeOptions(
                    allowed_tools=["WebSearch", "WebFetch"],
                    permission_mode="auto",
                    max_turns=3,
                ),
            )

            response_text = ""
            for message in result:
                if hasattr(message, "content"):
                    if isinstance(message.content, str):
                        response_text += message.content
                    elif isinstance(message.content, list):
                        for block in message.content:
                            if hasattr(block, "text"):
                                response_text += block.text

            if "NOT_FOUND" in response_text.upper():
                return None

            # Extract PDF URL
            pdf_urls = re.findall(
                r"https?://[^\s<>\"']+\.pdf(?:\?[^\s<>\"']*)?",
                response_text,
                re.IGNORECASE,
            )

            return pdf_urls[0] if pdf_urls else None

        except Exception:
            return None

    async def search_institutional_repository(
        self,
        title: str,
        institution: str | None = None,
    ) -> str | None:
        """Search institutional repositories for a paper.

        Args:
            title: Paper title
            institution: Optional institution name to search

        Returns:
            PDF URL if found, None otherwise
        """
        if not self.enabled or not self._check_sdk_available():
            return None

        await self._rate_limit_wait()

        from claude_code_sdk import ClaudeCodeOptions, query

        inst_str = f"at {institution}" if institution else ""

        search_prompt = f"""Search for this paper in institutional repositories {inst_str}:
"{title}"

Search repositories like:
1. University digital archives
2. DSpace repositories
3. EPrints repositories
4. Zenodo

If you find a direct PDF link, return ONLY the URL.
If not found, respond with: NOT_FOUND"""

        try:
            result = await query(
                prompt=search_prompt,
                options=ClaudeCodeOptions(
                    allowed_tools=["WebSearch", "WebFetch"],
                    permission_mode="auto",
                    max_turns=3,
                ),
            )

            response_text = ""
            for message in result:
                if hasattr(message, "content"):
                    if isinstance(message.content, str):
                        response_text += message.content
                    elif isinstance(message.content, list):
                        for block in message.content:
                            if hasattr(block, "text"):
                                response_text += block.text

            if "NOT_FOUND" in response_text.upper():
                return None

            pdf_urls = re.findall(
                r"https?://[^\s<>\"']+\.pdf(?:\?[^\s<>\"']*)?",
                response_text,
                re.IGNORECASE,
            )

            return pdf_urls[0] if pdf_urls else None

        except Exception:
            return None

    def is_available(self) -> bool:
        """Check if web search is available and enabled.

        Returns:
            True if enabled and SDK is available
        """
        return self.enabled and self._check_sdk_available()
