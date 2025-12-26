"""CrossRef API client for DOI resolution and metadata."""

from __future__ import annotations

from typing import Any, Optional

from .base import BaseClient, RateLimiter


class CrossRefClient(BaseClient):
    """Client for the CrossRef API.
    
    See: https://api.crossref.org/swagger-ui/index.html
    """
    
    BASE_URL = "https://api.crossref.org"
    
    def __init__(self, email: Optional[str] = None):
        """Initialize the CrossRef client.
        
        Args:
            email: Contact email (provides access to polite pool)
        """
        # CrossRef has generous limits, 50/sec in polite pool
        super().__init__(
            base_url=self.BASE_URL,
            rate_limiter=RateLimiter(calls_per_second=10.0),
        )
        
        self.email = email
        if email:
            # Use the polite pool
            self.set_header("User-Agent", f"ingestor/1.0 (mailto:{email})")
    
    async def get_paper_metadata(self, identifier: str) -> Optional[dict[str, Any]]:
        """Get paper metadata from CrossRef.
        
        Args:
            identifier: DOI
            
        Returns:
            Paper metadata dict or None
        """
        # Clean the DOI
        doi = identifier.strip()
        if doi.startswith("https://doi.org/"):
            doi = doi[16:]
        elif doi.startswith("http://dx.doi.org/"):
            doi = doi[18:]
        elif doi.lower().startswith("doi:"):
            doi = doi[4:]
        
        data = await self.get(f"works/{doi}")
        
        if not data or "message" not in data:
            return None
        
        msg = data["message"]
        
        # Extract authors
        authors = []
        for author in msg.get("author", []):
            name_parts = []
            if author.get("given"):
                name_parts.append(author["given"])
            if author.get("family"):
                name_parts.append(author["family"])
            
            authors.append({
                "name": " ".join(name_parts) if name_parts else "Unknown",
                "given": author.get("given"),
                "family": author.get("family"),
                "orcid": author.get("ORCID"),
                "affiliation": [a.get("name") for a in author.get("affiliation", [])],
            })
        
        # Get publication date
        pub_date = None
        date_parts = msg.get("published-print", {}).get("date-parts", [[]])
        if not date_parts or not date_parts[0]:
            date_parts = msg.get("published-online", {}).get("date-parts", [[]])
        
        if date_parts and date_parts[0]:
            parts = date_parts[0]
            if len(parts) >= 1:
                year = parts[0]
                month = parts[1] if len(parts) >= 2 else 1
                day = parts[2] if len(parts) >= 3 else 1
                pub_date = f"{year:04d}-{month:02d}-{day:02d}"
        
        # Get titles
        title = msg.get("title", [""])[0] if msg.get("title") else None
        subtitle = msg.get("subtitle", [""])[0] if msg.get("subtitle") else None
        
        # Combine title and subtitle
        full_title = title
        if subtitle:
            full_title = f"{title}: {subtitle}"
        
        return {
            "title": full_title,
            "authors": authors,
            "year": date_parts[0][0] if date_parts and date_parts[0] else None,
            "venue": msg.get("container-title", [""])[0] if msg.get("container-title") else None,
            "publisher": msg.get("publisher"),
            "abstract": msg.get("abstract"),
            "doi": msg.get("DOI"),
            "url": msg.get("URL"),
            "issn": msg.get("ISSN"),
            "isbn": msg.get("ISBN"),
            "volume": msg.get("volume"),
            "issue": msg.get("issue"),
            "page": msg.get("page"),
            "type": msg.get("type"),
            "subject": msg.get("subject"),
            "publication_date": pub_date,
            "citation_count": msg.get("is-referenced-by-count"),
            "reference_count": msg.get("references-count"),
            "license": [lic.get("URL") for lic in msg.get("license", [])],
            "link": [
                {"url": link.get("URL"), "type": link.get("content-type")}
                for link in msg.get("link", [])
            ],
            "source": "crossref",
        }
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        filter_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Search for works.
        
        Args:
            query: Search query
            limit: Maximum results
            filter_type: Filter by type (journal-article, book-chapter, etc.)
            
        Returns:
            List of paper metadata
        """
        params: dict[str, Any] = {
            "query": query,
            "rows": min(limit, 100),
        }
        
        if filter_type:
            params["filter"] = f"type:{filter_type}"
        
        data = await self.get("works", params=params)
        
        if not data or "message" not in data:
            return []
        
        results = []
        for item in data["message"].get("items", []):
            authors = []
            for author in item.get("author", []):
                name_parts = []
                if author.get("given"):
                    name_parts.append(author["given"])
                if author.get("family"):
                    name_parts.append(author["family"])
                authors.append(" ".join(name_parts) if name_parts else "Unknown")
            
            results.append({
                "title": item.get("title", [""])[0] if item.get("title") else None,
                "authors": authors,
                "year": item.get("published-print", {}).get("date-parts", [[None]])[0][0],
                "doi": item.get("DOI"),
                "venue": item.get("container-title", [""])[0] if item.get("container-title") else None,
                "type": item.get("type"),
            })
        
        return results
    
    async def get_bibtex(self, doi: str) -> Optional[str]:
        """Get BibTeX citation for a DOI.
        
        Args:
            doi: The DOI
            
        Returns:
            BibTeX string or None
        """
        await self.rate_limiter.wait()
        
        import httpx
        
        # Clean DOI
        if doi.startswith("https://doi.org/"):
            doi = doi[16:]
        elif doi.startswith("doi:"):
            doi = doi[4:]
        
        url = f"https://doi.org/{doi}"
        
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            try:
                response = await client.get(
                    url,
                    headers={
                        "Accept": "application/x-bibtex",
                        **self.headers,
                    },
                )
                response.raise_for_status()
                return response.text
            except Exception:
                return None
