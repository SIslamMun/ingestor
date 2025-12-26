"""Semantic Scholar API client."""

from __future__ import annotations

from typing import Any, Optional

from .base import BaseClient, RateLimiter


class SemanticScholarClient(BaseClient):
    """Client for the Semantic Scholar API.
    
    See: https://api.semanticscholar.org/api-docs/
    """
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    
    # Standard fields to request
    PAPER_FIELDS = [
        "title",
        "authors",
        "year",
        "venue",
        "abstract",
        "externalIds",
        "openAccessPdf",
        "citationCount",
        "referenceCount",
        "fieldsOfStudy",
        "publicationDate",
        "publicationTypes",
    ]
    
    AUTHOR_FIELDS = [
        "authorId",
        "name",
        "affiliations",
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Semantic Scholar client.
        
        Args:
            api_key: API key for higher rate limits
        """
        # Without API key: 100 requests per 5 minutes = ~0.33/sec
        # With API key: much higher limits
        rate = 0.33 if not api_key else 10.0
        super().__init__(
            base_url=self.BASE_URL,
            rate_limiter=RateLimiter(calls_per_second=rate),
        )
        
        self.api_key = api_key
        if api_key:
            self.set_header("x-api-key", api_key)
    
    def _format_paper_id(self, identifier: str) -> str:
        """Format identifier for S2 API.
        
        Args:
            identifier: DOI, arXiv ID, S2 ID, etc.
            
        Returns:
            Formatted identifier with proper prefix
        """
        identifier = identifier.strip()
        
        # Already has a prefix
        if any(identifier.startswith(p) for p in ["DOI:", "ARXIV:", "CorpusID:", "URL:", "PMID:", "MAG:"]):
            return identifier
        
        # Looks like a DOI
        if "/" in identifier and identifier.startswith("10."):
            return f"DOI:{identifier}"
        
        # Looks like an arXiv ID
        if identifier.startswith("arXiv:"):
            return f"ARXIV:{identifier[6:]}"
        
        # New-style arXiv (YYMM.NNNNN)
        if len(identifier) >= 9 and identifier[4] == "." and identifier[:4].isdigit():
            return f"ARXIV:{identifier}"
        
        # Looks like a Corpus ID
        if identifier.isdigit():
            return f"CorpusID:{identifier}"
        
        # 40-char hex is S2 paper ID
        if len(identifier) == 40 and all(c in "0123456789abcdef" for c in identifier.lower()):
            return identifier
        
        # Default: assume it's already formatted or use as-is
        return identifier
    
    async def get_paper_metadata(self, identifier: str) -> Optional[dict[str, Any]]:
        """Get paper metadata from Semantic Scholar.
        
        Args:
            identifier: DOI, arXiv ID, S2 corpus ID, or S2 paper ID
            
        Returns:
            Paper metadata dict or None
        """
        paper_id = self._format_paper_id(identifier)
        
        data = await self.get(
            f"paper/{paper_id}",
            params={"fields": ",".join(self.PAPER_FIELDS)},
        )
        
        if not data:
            return None
        
        # Normalize to common format
        return {
            "title": data.get("title"),
            "authors": [
                {
                    "name": author.get("name"),
                    "author_id": author.get("authorId"),
                }
                for author in data.get("authors", [])
            ],
            "year": data.get("year"),
            "venue": data.get("venue"),
            "abstract": data.get("abstract"),
            "doi": data.get("externalIds", {}).get("DOI"),
            "arxiv_id": data.get("externalIds", {}).get("ArXiv"),
            "pmid": data.get("externalIds", {}).get("PubMed"),
            "s2_id": data.get("paperId"),
            "s2_corpus_id": data.get("externalIds", {}).get("CorpusId"),
            "pdf_url": data.get("openAccessPdf", {}).get("url") if data.get("openAccessPdf") else None,
            "citation_count": data.get("citationCount"),
            "reference_count": data.get("referenceCount"),
            "fields_of_study": data.get("fieldsOfStudy"),
            "publication_date": data.get("publicationDate"),
            "publication_types": data.get("publicationTypes"),
            "source": "semantic_scholar",
        }
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        year_range: Optional[tuple[int, int]] = None,
        fields_of_study: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """Search for papers.
        
        Args:
            query: Search query (title, keywords, etc.)
            limit: Maximum results to return
            year_range: Optional (min_year, max_year) filter
            fields_of_study: Optional field filters (e.g., ["Computer Science"])
            
        Returns:
            List of paper metadata dicts
        """
        params: dict[str, Any] = {
            "query": query,
            "limit": min(limit, 100),  # API max is 100
            "fields": ",".join(self.PAPER_FIELDS),
        }
        
        if year_range:
            params["year"] = f"{year_range[0]}-{year_range[1]}"
        
        if fields_of_study:
            params["fieldsOfStudy"] = ",".join(fields_of_study)
        
        data = await self.get("paper/search", params=params)
        
        if not data or "data" not in data:
            return []
        
        results = []
        for paper in data["data"]:
            results.append({
                "title": paper.get("title"),
                "authors": [a.get("name") for a in paper.get("authors", [])],
                "year": paper.get("year"),
                "doi": paper.get("externalIds", {}).get("DOI"),
                "arxiv_id": paper.get("externalIds", {}).get("ArXiv"),
                "s2_id": paper.get("paperId"),
                "pdf_url": paper.get("openAccessPdf", {}).get("url") if paper.get("openAccessPdf") else None,
                "citation_count": paper.get("citationCount"),
            })
        
        return results
    
    async def get_citations(
        self,
        identifier: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get papers that cite this paper.
        
        Args:
            identifier: Paper identifier
            limit: Maximum citations to return
            
        Returns:
            List of citing paper metadata
        """
        paper_id = self._format_paper_id(identifier)
        
        data = await self.get(
            f"paper/{paper_id}/citations",
            params={
                "fields": "title,authors,year,externalIds,citationCount",
                "limit": min(limit, 1000),
            },
        )
        
        if not data or "data" not in data:
            return []
        
        results = []
        for item in data["data"]:
            paper = item.get("citingPaper", {})
            results.append({
                "title": paper.get("title"),
                "authors": [a.get("name") for a in paper.get("authors", [])],
                "year": paper.get("year"),
                "doi": paper.get("externalIds", {}).get("DOI"),
                "s2_id": paper.get("paperId"),
                "citation_count": paper.get("citationCount"),
            })
        
        return results
    
    async def get_references(
        self,
        identifier: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get papers referenced by this paper.
        
        Args:
            identifier: Paper identifier
            limit: Maximum references to return
            
        Returns:
            List of referenced paper metadata
        """
        paper_id = self._format_paper_id(identifier)
        
        data = await self.get(
            f"paper/{paper_id}/references",
            params={
                "fields": "title,authors,year,externalIds,citationCount",
                "limit": min(limit, 1000),
            },
        )
        
        if not data or "data" not in data:
            return []
        
        results = []
        for item in data["data"]:
            paper = item.get("citedPaper", {})
            if paper:  # Some references might not be in S2
                external_ids = paper.get("externalIds") or {}
                results.append({
                    "title": paper.get("title"),
                    "authors": [a.get("name") for a in paper.get("authors", [])],
                    "year": paper.get("year"),
                    "doi": external_ids.get("DOI"),
                    "s2_id": paper.get("paperId"),
                    "citation_count": paper.get("citationCount"),
                })
        
        return results
