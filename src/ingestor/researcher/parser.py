"""Parser for extracting references from research documents.

Takes in a research document and generates a list of PDFs, websites,
citations, git repos, YouTube videos, podcasts, books, etc. referenced in it.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class ReferenceType(Enum):
    """Types of references that can be extracted."""
    GITHUB = "github"
    ARXIV = "arxiv"
    DOI = "doi"
    PAPER = "paper"
    PDF = "pdf"
    YOUTUBE = "youtube"
    PODCAST = "podcast"
    BOOK = "book"
    WEBSITE = "website"


@dataclass
class ParsedReference:
    """A reference extracted from research output."""
    type: ReferenceType
    value: str
    title: str = ""
    authors: str = ""
    year: str = ""
    url: Optional[str] = None
    context: str = ""
    metadata: dict = field(default_factory=dict)


class ResearchParser:
    """Parser for extracting references from research documents.
    
    Takes in a research document and generates a categorized list of:
    - PDFs
    - Websites
    - Citations (papers)
    - Git repositories
    - YouTube videos
    - Podcasts
    - Books
    
    Example:
        ```python
        parser = ResearchParser()
        refs = parser.parse_file("research_report.md")
        
        # Get summary
        summary = parser.get_summary(refs)
        print(summary)
        
        # Get by category
        github_repos = [r for r in refs if r.type == ReferenceType.GITHUB]
        ```
    """
    
    def __init__(self):
        """Initialize the parser."""
        pass
    
    def parse(self, text: str) -> list[ParsedReference]:
        """Parse text and extract all references.
        
        Args:
            text: Text content to parse
            
        Returns:
            List of parsed references
        """
        references = []
        
        # Extract GitHub repos
        references.extend(self._extract_github(text))
        
        # Extract arXiv papers
        references.extend(self._extract_arxiv(text))
        
        # Extract DOIs
        references.extend(self._extract_doi(text))
        
        # Extract paper citations (Author et al., Year)
        references.extend(self._extract_papers(text))
        
        # Extract PDFs
        references.extend(self._extract_pdfs(text))
        
        # Extract YouTube
        references.extend(self._extract_youtube(text))
        
        # Extract podcasts
        references.extend(self._extract_podcasts(text))
        
        # Extract books
        references.extend(self._extract_books(text))
        
        # Extract general websites
        references.extend(self._extract_websites(text))
        
        # Deduplicate
        references = self._deduplicate(references)
        
        return references
    
    def parse_file(self, file_path: Path) -> list[ParsedReference]:
        """Parse a file and extract references.
        
        Args:
            file_path: Path to file
            
        Returns:
            List of parsed references
        """
        file_path = Path(file_path)
        
        if file_path.suffix == ".json":
            import json
            with open(file_path) as f:
                data = json.load(f)
            if isinstance(data, dict):
                text = data.get("report", data.get("content", str(data)))
            else:
                text = str(data)
        else:
            text = file_path.read_text()
        
        return self.parse(text)
    
    def _extract_github(self, text: str) -> list[ParsedReference]:
        """Extract GitHub repositories."""
        refs = []
        seen = set()
        
        patterns = [
            # **Repository:** `owner/repo`
            r'\*\*Repository:\*\*\s*`([a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+)`',
            # `owner/repo` format
            r'`([a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+)`',
            # GitHub URLs
            r'github\.com/([a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+)',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                repo = match.group(1).rstrip('/')
                # Clean up repo name
                repo = repo.split('/tree/')[0].split('/blob/')[0]
                
                if repo not in seen and '/' in repo:
                    seen.add(repo)
                    refs.append(ParsedReference(
                        type=ReferenceType.GITHUB,
                        value=repo,
                        title=repo.split('/')[-1],
                        url=f"https://github.com/{repo}",
                        context=self._get_context(text, match),
                    ))
        
        return refs
    
    def _extract_arxiv(self, text: str) -> list[ParsedReference]:
        """Extract arXiv papers."""
        refs = []
        seen = set()
        
        patterns = [
            r'arXiv[:\s]+(\d{4}\.\d{4,5}(?:v\d+)?)',
            r'arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?)',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                arxiv_id = match.group(1)
                if arxiv_id not in seen:
                    seen.add(arxiv_id)
                    refs.append(ParsedReference(
                        type=ReferenceType.ARXIV,
                        value=arxiv_id,
                        url=f"https://arxiv.org/abs/{arxiv_id}",
                        context=self._get_context(text, match),
                    ))
        
        return refs
    
    def _extract_doi(self, text: str) -> list[ParsedReference]:
        """Extract DOIs."""
        refs = []
        seen = set()
        
        patterns = [
            r'(?:doi[:\s]+)?(10\.\d{4,}/[^\s\]\),]+)',
            r'doi\.org/(10\.\d{4,}/[^\s\]\),]+)',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                doi = match.group(1).rstrip('.,;')
                if doi not in seen:
                    seen.add(doi)
                    refs.append(ParsedReference(
                        type=ReferenceType.DOI,
                        value=doi,
                        url=f"https://doi.org/{doi}",
                        context=self._get_context(text, match),
                    ))
        
        return refs
    
    def _extract_papers(self, text: str) -> list[ParsedReference]:
        """Extract paper citations."""
        refs = []
        seen = set()
        
        # **Paper:** *Title*
        paper_pattern = r'\*\*Paper:\*\*\s*\*([^*]+)\*'
        for match in re.finditer(paper_pattern, text):
            title = match.group(1).strip()
            if title.lower() not in seen:
                seen.add(title.lower())
                refs.append(ParsedReference(
                    type=ReferenceType.PAPER,
                    value=title,
                    title=title,
                    context=self._get_context(text, match),
                ))
        
        # **Authors:** Author et al. **Year:** 2020
        author_pattern = r'\*\*Authors:\*\*\s*([^*\n]+?)(?:\*\*Year:\*\*\s*(\d{4}))?'
        
        # Title (Author et al., Year)
        cite_pattern = r'"([^"]{15,200})"\s*\(([A-Z][a-z]+(?:\s+et\s+al\.?)?),?\s*(\d{4})\)'
        for match in re.finditer(cite_pattern, text):
            title = match.group(1).strip()
            authors = match.group(2)
            year = match.group(3)
            if title.lower() not in seen:
                seen.add(title.lower())
                refs.append(ParsedReference(
                    type=ReferenceType.PAPER,
                    value=title,
                    title=title,
                    authors=authors,
                    year=year,
                    context=match.group(0),
                ))
        
        return refs
    
    def _extract_pdfs(self, text: str) -> list[ParsedReference]:
        """Extract PDF links."""
        refs = []
        seen = set()
        
        pattern = r'(https?://[^\s\]\)]+\.pdf)'
        for match in re.finditer(pattern, text, re.IGNORECASE):
            url = match.group(1)
            if url not in seen:
                seen.add(url)
                refs.append(ParsedReference(
                    type=ReferenceType.PDF,
                    value=url,
                    url=url,
                    context=self._get_context(text, match),
                ))
        
        return refs
    
    def _extract_youtube(self, text: str) -> list[ParsedReference]:
        """Extract YouTube videos."""
        refs = []
        seen = set()
        
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                video_id = match.group(1)
                if video_id not in seen:
                    seen.add(video_id)
                    refs.append(ParsedReference(
                        type=ReferenceType.YOUTUBE,
                        value=video_id,
                        url=f"https://youtube.com/watch?v={video_id}",
                        context=self._get_context(text, match),
                    ))
        
        return refs
    
    def _extract_podcasts(self, text: str) -> list[ParsedReference]:
        """Extract podcast references."""
        refs = []
        seen = set()
        
        # Podcast mentions
        patterns = [
            r'(?:podcast|episode)[:\s]+["\']([^"\']+)["\']',
            r'(spotify\.com/(?:show|episode)/[^\s\]\)]+)',
            r'(podcasts\.apple\.com/[^\s\]\)]+)',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = match.group(1)
                if value.lower() not in seen:
                    seen.add(value.lower())
                    url = value if value.startswith('http') or '.' in value else None
                    refs.append(ParsedReference(
                        type=ReferenceType.PODCAST,
                        value=value,
                        url=f"https://{url}" if url and not url.startswith('http') else url,
                        context=self._get_context(text, match),
                    ))
        
        return refs
    
    def _extract_books(self, text: str) -> list[ParsedReference]:
        """Extract book references."""
        refs = []
        seen = set()
        
        # Book patterns
        patterns = [
            # "Book Title" by Author
            r'"([^"]{10,100})"\s+by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            # ISBN
            r'ISBN[:\s-]*(\d{10}|\d{13})',
            # **Book:** Title
            r'\*\*Book:\*\*\s*\*?([^*\n]+)\*?',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                if 'ISBN' in pattern:
                    value = f"ISBN: {match.group(1)}"
                    title = ""
                else:
                    value = match.group(1).strip()
                    title = value
                
                if value.lower() not in seen:
                    seen.add(value.lower())
                    refs.append(ParsedReference(
                        type=ReferenceType.BOOK,
                        value=value,
                        title=title,
                        authors=match.group(2) if match.lastindex >= 2 else "",
                        context=self._get_context(text, match),
                    ))
        
        return refs
    
    def _extract_websites(self, text: str) -> list[ParsedReference]:
        """Extract general website URLs."""
        refs = []
        seen = set()
        
        # Skip patterns for other types
        skip_patterns = [
            'github.com', 'arxiv.org', 'doi.org', 'youtube.com', 'youtu.be',
            'spotify.com', 'podcasts.apple.com', '.pdf',
            'vertexaisearch.cloud.google.com',  # Skip redirect URLs
        ]
        
        pattern = r'https?://[^\s\]\)>]+'
        for match in re.finditer(pattern, text):
            url = match.group(0).rstrip('.,;:"\'])')
            
            # Skip if matches other types
            if any(skip in url.lower() for skip in skip_patterns):
                continue
            
            if url not in seen:
                seen.add(url)
                # Extract domain as title
                domain = re.search(r'https?://([^/]+)', url)
                title = domain.group(1) if domain else url
                
                refs.append(ParsedReference(
                    type=ReferenceType.WEBSITE,
                    value=url,
                    title=title,
                    url=url,
                    context=self._get_context(text, match),
                ))
        
        return refs
    
    def _get_context(self, text: str, match) -> str:
        """Get surrounding context for a match."""
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        return text[start:end].strip()
    
    def _deduplicate(self, refs: list[ParsedReference]) -> list[ParsedReference]:
        """Remove duplicate references."""
        seen = set()
        unique = []
        
        for ref in refs:
            key = (ref.type, ref.value.lower())
            if key not in seen:
                seen.add(key)
                unique.append(ref)
        
        return unique
    
    def group_by_type(self, refs: list[ParsedReference]) -> dict[ReferenceType, list[ParsedReference]]:
        """Group references by type."""
        grouped = {}
        for ref in refs:
            if ref.type not in grouped:
                grouped[ref.type] = []
            grouped[ref.type].append(ref)
        return grouped
    
    def get_summary(self, refs: list[ParsedReference]) -> str:
        """Generate a summary of extracted references.
        
        Args:
            refs: List of references
            
        Returns:
            Formatted summary string
        """
        grouped = self.group_by_type(refs)
        
        lines = ["# Extracted References\n"]
        
        type_names = {
            ReferenceType.GITHUB: "GitHub Repositories",
            ReferenceType.ARXIV: "arXiv Papers",
            ReferenceType.DOI: "DOI Citations",
            ReferenceType.PAPER: "Paper Citations",
            ReferenceType.PDF: "PDF Documents",
            ReferenceType.YOUTUBE: "YouTube Videos",
            ReferenceType.PODCAST: "Podcasts",
            ReferenceType.BOOK: "Books",
            ReferenceType.WEBSITE: "Websites",
        }
        
        for ref_type in ReferenceType:
            if ref_type in grouped:
                type_refs = grouped[ref_type]
                lines.append(f"\n## {type_names.get(ref_type, ref_type.value)} ({len(type_refs)})\n")
                
                for ref in type_refs:
                    if ref.url:
                        lines.append(f"- [{ref.value}]({ref.url})")
                    else:
                        lines.append(f"- {ref.value}")
                    
                    if ref.authors or ref.year:
                        extra = []
                        if ref.authors:
                            extra.append(ref.authors)
                        if ref.year:
                            extra.append(ref.year)
                        lines.append(f"  - {', '.join(extra)}")
        
        # Summary stats
        lines.append(f"\n---\n**Total: {len(refs)} references**")
        
        return "\n".join(lines)
    
    def save_summary(self, refs: list[ParsedReference], output_path: Path) -> Path:
        """Save summary to a file.
        
        Args:
            refs: List of references
            output_path: Output directory or file path
            
        Returns:
            Path to saved file
        """
        output_path = Path(output_path)
        
        if output_path.is_dir():
            output_path = output_path / "extracted_references.md"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.get_summary(refs))
        
        return output_path
