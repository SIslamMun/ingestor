"""OpenAlex API client for academic metadata."""

from __future__ import annotations

from typing import Any, Optional

from .base import BaseClient, RateLimiter


class OpenAlexClient(BaseClient):
    """Client for the OpenAlex API.
    
    See: https://docs.openalex.org/
    """
    
    BASE_URL = "https://api.openalex.org"
    
    def __init__(self, email: Optional[str] = None):
        """Initialize the OpenAlex client.
        
        Args:
            email: Contact email (for polite pool, higher rate limits)
        """
        # OpenAlex: 100k/day = ~1/sec without email, 10/sec with email
        rate = 10.0 if email else 1.0
        super().__init__(
            base_url=self.BASE_URL,
            rate_limiter=RateLimiter(calls_per_second=rate),
        )
        
        self.email = email
    
    def _add_email_param(self, params: dict[str, Any]) -> dict[str, Any]:
        """Add email to params for polite pool."""
        if self.email:
            params["mailto"] = self.email
        return params
    
    async def get_paper_metadata(self, identifier: str) -> Optional[dict[str, Any]]:
        """Get paper metadata from OpenAlex.
        
        Args:
            identifier: DOI, OpenAlex ID, or other identifier
            
        Returns:
            Paper metadata dict or None
        """
        identifier = identifier.strip()
        
        # Determine the lookup key
        if identifier.startswith("W"):
            # OpenAlex Work ID
            work_id = identifier
        elif identifier.startswith("https://openalex.org/"):
            work_id = identifier.split("/")[-1]
        elif "/" in identifier and identifier.startswith("10."):
            # DOI
            work_id = f"https://doi.org/{identifier}"
        else:
            # Try as DOI
            work_id = f"https://doi.org/{identifier}"
        
        params = self._add_email_param({})
        data = await self.get(f"works/{work_id}", params=params)
        
        if not data:
            return None
        
        # Extract authors
        authors = []
        for authorship in data.get("authorships", []):
            author = authorship.get("author", {})
            institutions = [
                inst.get("display_name")
                for inst in authorship.get("institutions", [])
            ]
            authors.append({
                "name": author.get("display_name"),
                "orcid": author.get("orcid"),
                "openalex_id": author.get("id"),
                "affiliations": institutions,
            })
        
        # Get primary location
        primary_loc = data.get("primary_location", {}) or {}
        source = primary_loc.get("source", {}) or {}
        
        # Get best OA URL
        pdf_url = None
        for loc in data.get("locations", []):
            if loc.get("pdf_url"):
                pdf_url = loc["pdf_url"]
                break
        if not pdf_url:
            pdf_url = data.get("open_access", {}).get("oa_url")
        
        return {
            "title": data.get("title"),
            "authors": authors,
            "year": data.get("publication_year"),
            "venue": source.get("display_name"),
            "publisher": source.get("host_organization_name"),
            "abstract": self._reconstruct_abstract(data.get("abstract_inverted_index")),
            "doi": data.get("doi", "").replace("https://doi.org/", "") if data.get("doi") else None,
            "openalex_id": data.get("id"),
            "pmid": data.get("ids", {}).get("pmid"),
            "pmcid": data.get("ids", {}).get("pmcid"),
            "pdf_url": pdf_url,
            "is_open_access": data.get("open_access", {}).get("is_oa"),
            "oa_status": data.get("open_access", {}).get("oa_status"),
            "citation_count": data.get("cited_by_count"),
            "reference_count": len(data.get("referenced_works", [])),
            "concepts": [
                {"name": c.get("display_name"), "score": c.get("score")}
                for c in data.get("concepts", [])[:5]  # Top 5 concepts
            ],
            "type": data.get("type"),
            "publication_date": data.get("publication_date"),
            "source": "openalex",
        }
    
    def _reconstruct_abstract(self, inverted_index: Optional[dict]) -> Optional[str]:
        """Reconstruct abstract from inverted index.
        
        OpenAlex stores abstracts as inverted indices to save space.
        """
        if not inverted_index:
            return None
        
        # Build position -> word mapping
        positions: dict[int, str] = {}
        for word, indices in inverted_index.items():
            for idx in indices:
                positions[idx] = word
        
        # Reconstruct in order
        if not positions:
            return None
        
        max_pos = max(positions.keys())
        words = [positions.get(i, "") for i in range(max_pos + 1)]
        return " ".join(words)
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        filter_open_access: bool = False,
        filter_year: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Search for works.
        
        Args:
            query: Search query
            limit: Maximum results
            filter_open_access: Only return open access works
            filter_year: Filter by publication year
            
        Returns:
            List of paper metadata
        """
        params: dict[str, Any] = {
            "search": query,
            "per_page": min(limit, 200),
        }
        
        filters = []
        if filter_open_access:
            filters.append("open_access.is_oa:true")
        if filter_year:
            filters.append(f"publication_year:{filter_year}")
        
        if filters:
            params["filter"] = ",".join(filters)
        
        params = self._add_email_param(params)
        data = await self.get("works", params=params)
        
        if not data or "results" not in data:
            return []
        
        results = []
        for work in data["results"]:
            authors = [
                a.get("author", {}).get("display_name")
                for a in work.get("authorships", [])
            ]
            
            results.append({
                "title": work.get("title"),
                "authors": authors,
                "year": work.get("publication_year"),
                "doi": work.get("doi", "").replace("https://doi.org/", "") if work.get("doi") else None,
                "openalex_id": work.get("id"),
                "is_open_access": work.get("open_access", {}).get("is_oa"),
                "citation_count": work.get("cited_by_count"),
            })
        
        return results
    
    async def get_citations(
        self,
        identifier: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get works that cite this work.
        
        Args:
            identifier: Work identifier (DOI or OpenAlex ID)
            limit: Maximum citations
            
        Returns:
            List of citing work metadata
        """
        # First get the OpenAlex ID
        metadata = await self.get_paper_metadata(identifier)
        if not metadata or not metadata.get("openalex_id"):
            return []
        
        openalex_id = metadata["openalex_id"]
        
        params = self._add_email_param({
            "filter": f"cites:{openalex_id}",
            "per_page": min(limit, 200),
        })
        
        data = await self.get("works", params=params)
        
        if not data or "results" not in data:
            return []
        
        results = []
        for work in data["results"]:
            authors = [
                a.get("author", {}).get("display_name")
                for a in work.get("authorships", [])
            ]
            
            results.append({
                "title": work.get("title"),
                "authors": authors,
                "year": work.get("publication_year"),
                "doi": work.get("doi", "").replace("https://doi.org/", "") if work.get("doi") else None,
                "openalex_id": work.get("id"),
                "citation_count": work.get("cited_by_count"),
            })
        
        return results
    
    async def get_references(
        self,
        identifier: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get works referenced by this work.
        
        Args:
            identifier: Work identifier
            limit: Maximum references
            
        Returns:
            List of referenced work metadata
        """
        # Get the work to find referenced_works IDs
        identifier = identifier.strip()
        
        if identifier.startswith("W"):
            work_id = identifier
        elif "/" in identifier and identifier.startswith("10."):
            work_id = f"https://doi.org/{identifier}"
        else:
            work_id = identifier
        
        params = self._add_email_param({})
        data = await self.get(f"works/{work_id}", params=params)
        
        if not data or "referenced_works" not in data:
            return []
        
        # Get details for each referenced work
        ref_ids = data["referenced_works"][:limit]
        
        if not ref_ids:
            return []
        
        # Batch query referenced works
        filter_str = "|".join(ref_ids)
        params = self._add_email_param({
            "filter": f"openalex_id:{filter_str}",
            "per_page": min(len(ref_ids), 200),
        })
        
        ref_data = await self.get("works", params=params)
        
        if not ref_data or "results" not in ref_data:
            return []
        
        results = []
        for work in ref_data["results"]:
            authors = [
                a.get("author", {}).get("display_name")
                for a in work.get("authorships", [])
            ]
            
            results.append({
                "title": work.get("title"),
                "authors": authors,
                "year": work.get("publication_year"),
                "doi": work.get("doi", "").replace("https://doi.org/", "") if work.get("doi") else None,
                "openalex_id": work.get("id"),
                "citation_count": work.get("cited_by_count"),
            })
        
        return results
