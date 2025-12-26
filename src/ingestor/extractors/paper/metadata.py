"""Paper metadata extraction and BibTeX generation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .resolver import PaperIdentifier, IdentifierType


@dataclass
class Author:
    """Paper author information."""
    
    name: str
    given: Optional[str] = None
    family: Optional[str] = None
    orcid: Optional[str] = None
    affiliations: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "given": self.given,
            "family": self.family,
            "orcid": self.orcid,
            "affiliations": self.affiliations,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Author":
        """Create from dictionary."""
        return cls(
            name=data.get("name", "Unknown"),
            given=data.get("given"),
            family=data.get("family"),
            orcid=data.get("orcid"),
            affiliations=data.get("affiliations", []),
        )


@dataclass
class PaperMetadata:
    """Complete paper metadata."""
    
    title: str
    authors: list[Author] = field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    publisher: Optional[str] = None
    abstract: Optional[str] = None
    
    # Identifiers
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    s2_id: Optional[str] = None
    openalex_id: Optional[str] = None
    
    # URLs
    pdf_url: Optional[str] = None
    url: Optional[str] = None
    
    # Citation info
    citation_count: Optional[int] = None
    reference_count: Optional[int] = None
    
    # Additional metadata
    keywords: list[str] = field(default_factory=list)
    subjects: list[str] = field(default_factory=list)
    publication_date: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publication_type: Optional[str] = None
    
    # Data source
    source: Optional[str] = None
    
    @property
    def first_author(self) -> str:
        """Get first author name."""
        if self.authors:
            return self.authors[0].name
        return "Unknown"
    
    @property
    def first_author_last_name(self) -> str:
        """Get first author's last name."""
        if self.authors:
            author = self.authors[0]
            if author.family:
                return author.family
            # Try to extract from full name
            parts = author.name.split()
            return parts[-1] if parts else "Unknown"
        return "Unknown"
    
    @property
    def author_string(self) -> str:
        """Get formatted author string."""
        if not self.authors:
            return "Unknown"
        
        names = [a.name for a in self.authors]
        
        if len(names) == 1:
            return names[0]
        elif len(names) == 2:
            return f"{names[0]} and {names[1]}"
        else:
            return f"{names[0]} et al."
    
    @property
    def bibtex_key(self) -> str:
        """Generate BibTeX citation key."""
        # Format: LastName + Year + FirstWordOfTitle
        last_name = re.sub(r"[^\w]", "", self.first_author_last_name.lower())
        year = str(self.year) if self.year else "0000"
        
        # Get first significant word from title
        if self.title:
            # Skip common articles
            skip_words = {"a", "an", "the", "on", "in", "of", "for", "to"}
            words = self.title.lower().split()
            first_word = ""
            for word in words:
                clean = re.sub(r"[^\w]", "", word)
                if clean and clean not in skip_words:
                    first_word = clean
                    break
        else:
            first_word = "paper"
        
        return f"{last_name}{year}{first_word}"
    
    def to_bibtex(self, key: Optional[str] = None) -> str:
        """Generate BibTeX entry.
        
        Args:
            key: Custom citation key (uses auto-generated if None)
            
        Returns:
            BibTeX string
        """
        key = key or self.bibtex_key
        
        # Determine entry type
        if self.arxiv_id and not self.venue:
            entry_type = "misc"  # arXiv preprint
        elif self.publication_type == "book-chapter":
            entry_type = "incollection"
        elif self.publication_type == "proceedings-article":
            entry_type = "inproceedings"
        elif self.publication_type == "book":
            entry_type = "book"
        else:
            entry_type = "article"
        
        # Build fields
        fields = []
        
        # Title
        if self.title:
            # Escape special characters and wrap in braces
            title = self.title.replace("{", "\\{").replace("}", "\\}")
            fields.append(f'  title = {{{title}}}')
        
        # Authors
        if self.authors:
            author_str = " and ".join(a.name for a in self.authors)
            fields.append(f'  author = {{{author_str}}}')
        
        # Year
        if self.year:
            fields.append(f'  year = {{{self.year}}}')
        
        # Venue/Journal/Booktitle
        if self.venue:
            venue = self.venue.replace("{", "\\{").replace("}", "\\}")
            if entry_type in ("inproceedings", "incollection"):
                fields.append(f'  booktitle = {{{venue}}}')
            else:
                fields.append(f'  journal = {{{venue}}}')
        
        # Publisher
        if self.publisher:
            fields.append(f'  publisher = {{{self.publisher}}}')
        
        # Volume, Issue, Pages
        if self.volume:
            fields.append(f'  volume = {{{self.volume}}}')
        if self.issue:
            fields.append(f'  number = {{{self.issue}}}')
        if self.pages:
            fields.append(f'  pages = {{{self.pages}}}')
        
        # DOI
        if self.doi:
            fields.append(f'  doi = {{{self.doi}}}')
        
        # arXiv
        if self.arxiv_id:
            fields.append(f'  eprint = {{{self.arxiv_id}}}')
            fields.append('  archiveprefix = {arXiv}')
            if self.subjects:
                fields.append(f'  primaryclass = {{{self.subjects[0]}}}')
        
        # URL
        if self.url:
            fields.append(f'  url = {{{self.url}}}')
        elif self.pdf_url:
            fields.append(f'  url = {{{self.pdf_url}}}')
        
        # Abstract
        if self.abstract:
            abstract = self.abstract.replace("{", "\\{").replace("}", "\\}")
            abstract = abstract.replace("\n", " ")
            fields.append(f'  abstract = {{{abstract}}}')
        
        # Keywords
        if self.keywords:
            kw_str = ", ".join(self.keywords)
            fields.append(f'  keywords = {{{kw_str}}}')
        
        # Build entry
        fields_str = ",\n".join(fields)
        return f"@{entry_type}{{{key},\n{fields_str}\n}}"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "authors": [a.to_dict() for a in self.authors],
            "year": self.year,
            "venue": self.venue,
            "publisher": self.publisher,
            "abstract": self.abstract,
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
            "pmid": self.pmid,
            "pmcid": self.pmcid,
            "s2_id": self.s2_id,
            "openalex_id": self.openalex_id,
            "pdf_url": self.pdf_url,
            "url": self.url,
            "citation_count": self.citation_count,
            "reference_count": self.reference_count,
            "keywords": self.keywords,
            "subjects": self.subjects,
            "publication_date": self.publication_date,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "publication_type": self.publication_type,
            "source": self.source,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PaperMetadata":
        """Create from dictionary."""
        authors = [
            Author.from_dict(a) if isinstance(a, dict) else Author(name=str(a))
            for a in data.get("authors", [])
        ]
        
        return cls(
            title=data.get("title", "Unknown Title"),
            authors=authors,
            year=data.get("year"),
            venue=data.get("venue"),
            publisher=data.get("publisher"),
            abstract=data.get("abstract"),
            doi=data.get("doi"),
            arxiv_id=data.get("arxiv_id"),
            pmid=data.get("pmid"),
            pmcid=data.get("pmcid"),
            s2_id=data.get("s2_id"),
            openalex_id=data.get("openalex_id"),
            pdf_url=data.get("pdf_url"),
            url=data.get("url"),
            citation_count=data.get("citation_count"),
            reference_count=data.get("reference_count"),
            keywords=data.get("keywords", []),
            subjects=data.get("subjects", data.get("categories", [])),
            publication_date=data.get("publication_date"),
            volume=data.get("volume"),
            issue=data.get("issue"),
            pages=data.get("pages", data.get("page")),
            publication_type=data.get("publication_type", data.get("type")),
            source=data.get("source"),
        )


async def get_metadata(
    identifier: PaperIdentifier,
    email: Optional[str] = None,
    s2_api_key: Optional[str] = None,
) -> Optional[PaperMetadata]:
    """Get paper metadata from available sources.
    
    Tries multiple sources in order of reliability:
    1. CrossRef (for DOIs) - most authoritative
    2. Semantic Scholar - comprehensive coverage
    3. OpenAlex - good open access info
    4. arXiv (for arXiv IDs) - preprints
    
    Args:
        identifier: Resolved paper identifier
        email: Email for API access (CrossRef, Unpaywall, OpenAlex)
        s2_api_key: Semantic Scholar API key
        
    Returns:
        PaperMetadata or None
    """
    from .clients import (
        CrossRefClient,
        SemanticScholarClient,
        OpenAlexClient,
        ArxivClient,
    )
    
    metadata: Optional[dict[str, Any]] = None
    
    # Try sources based on identifier type
    # Check ARXIV first since arXiv papers also have DOIs
    if identifier.type == IdentifierType.ARXIV:
        arxiv_id = identifier.arxiv_id or identifier.value
        
        # Try arXiv first
        arxiv = ArxivClient()
        metadata = await arxiv.get_paper_metadata(arxiv_id)
        
        # Enhance with Semantic Scholar
        if metadata:
            s2 = SemanticScholarClient(api_key=s2_api_key)
            s2_meta = await s2.get_paper_metadata(f"ARXIV:{arxiv_id}")
            if s2_meta:
                # Merge citation info
                metadata["citation_count"] = s2_meta.get("citation_count")
                metadata["s2_id"] = s2_meta.get("s2_id")
    
    elif identifier.type == IdentifierType.DOI:
        doi = identifier.doi or identifier.value
        
        # Try CrossRef first
        if email:
            crossref = CrossRefClient(email=email)
            metadata = await crossref.get_paper_metadata(doi)
        
        # Fallback to Semantic Scholar
        if not metadata:
            s2 = SemanticScholarClient(api_key=s2_api_key)
            metadata = await s2.get_paper_metadata(doi)
        
        # Fallback to OpenAlex
        if not metadata and email:
            openalex = OpenAlexClient(email=email)
            metadata = await openalex.get_paper_metadata(doi)
    
    elif identifier.type == IdentifierType.SEMANTIC_SCHOLAR:
        s2 = SemanticScholarClient(api_key=s2_api_key)
        metadata = await s2.get_paper_metadata(identifier.value)
    
    elif identifier.type == IdentifierType.OPENALEX:
        if email:
            openalex = OpenAlexClient(email=email)
            metadata = await openalex.get_paper_metadata(identifier.value)
    
    elif identifier.type == IdentifierType.TITLE:
        # Search by title
        s2 = SemanticScholarClient(api_key=s2_api_key)
        results = await s2.search(identifier.value, limit=1)
        if results:
            # Get full metadata for top result
            top_result = results[0]
            if top_result.get("s2_id"):
                metadata = await s2.get_paper_metadata(top_result["s2_id"])
            elif top_result.get("doi"):
                metadata = await s2.get_paper_metadata(top_result["doi"])
    
    if not metadata:
        return None
    
    return PaperMetadata.from_dict(metadata)
