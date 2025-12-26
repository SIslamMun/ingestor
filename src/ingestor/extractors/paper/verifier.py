"""Citation verification and enrichment tool.

Inspired by doi2bib - verifies BibTeX citations against:
- CrossRef (via doi2bib)
- arXiv API
- Semantic Scholar

Outputs:
- verified.bib: Successfully verified citations
- failed.bib: Citations that couldn't be verified
- report.md: Summary report
"""

from __future__ import annotations

import asyncio
import re
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import xml.etree.ElementTree as ET


# Website URL patterns (no DOI expected)
WEBSITE_PATTERNS = [
    r"github\.com",
    r"github\.io",
    r"nsf\.gov",
    r"whitehouse\.gov",
    r"\.gov/",
    r"us-rse\.org",
    r"software\.ac\.uk",
    r"\.edu/",
    r"langchain\.com",
    r"openai\.com",
    r"anthropic\.com",
    r"huggingface\.co",
    r"docs\.",
    r"pypi\.org",
    r"npmjs\.com",
    r"readthedocs\.io",
]

# Paper repositories (these ARE papers, should have DOIs)
PAPER_REPO_PATTERNS = [
    r"arxiv\.org",
    r"proceedings\.neurips\.cc",
    r"openreview\.net",
    r"proceedings\.mlr\.press",
    r"aclanthology\.org",
    r"papers\.nips\.cc",
    r"dl\.acm\.org",
    r"ieee\.org",
    r"springer\.com",
    r"nature\.com",
    r"science\.org",
]


@dataclass
class BibEntry:
    """Parsed BibTeX entry."""
    
    key: str
    entry_type: str
    raw: str
    doi: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    eprint: Optional[str] = None  # arXiv ID
    booktitle: Optional[str] = None
    howpublished: Optional[str] = None
    is_arxiv: bool = False
    
    @classmethod
    def parse(cls, raw: str) -> Optional["BibEntry"]:
        """Parse a raw BibTeX entry."""
        raw = raw.strip()
        if not raw or not raw.startswith("@"):
            return None
        
        # Extract type and key
        match = re.match(r"@(\w+)\{([^,]+),", raw)
        if not match:
            return None
        
        entry = cls(
            key=match.group(2).strip(),
            entry_type=match.group(1).lower(),
            raw=raw,
        )
        
        # Extract common fields
        for field_name in ["doi", "url", "title", "author", "eprint", "booktitle", "howpublished"]:
            field_match = re.search(
                rf"\b{field_name}\s*=\s*\{{([^}}]+)\}}",
                raw,
                re.IGNORECASE,
            )
            if field_match:
                setattr(entry, field_name, field_match.group(1).strip())
        
        # Check archivePrefix
        archive_match = re.search(r"\barchivePrefix\s*=\s*\{([^}]+)\}", raw, re.IGNORECASE)
        entry.is_arxiv = archive_match and archive_match.group(1).lower() == "arxiv"
        
        return entry


@dataclass
class VerificationResult:
    """Result of verifying a single entry."""
    
    key: str
    status: str  # verified, arxiv, searched, website, manual, failed
    bibtex: str
    message: str
    source_file: Optional[str] = None


@dataclass
class VerificationStats:
    """Statistics from verification."""
    
    verified: int = 0
    arxiv: int = 0
    searched: int = 0
    website: int = 0
    manual: int = 0
    failed: int = 0
    
    @property
    def total_verified(self) -> int:
        return self.verified + self.arxiv + self.searched + self.website + self.manual
    
    @property
    def total(self) -> int:
        return self.total_verified + self.failed


def clean_doi(doi: Optional[str]) -> str:
    """Clean DOI field of common formatting issues."""
    if not doi:
        return ""
    # Remove "DOI " prefix (case insensitive)
    doi = re.sub(r"^DOI\s+", "", doi.strip(), flags=re.IGNORECASE)
    # Remove surrounding braces and whitespace
    doi = doi.strip("{}").strip()
    return doi


def normalize(s: str) -> str:
    """Normalize string for comparison."""
    if not s:
        return ""
    # Remove LaTeX commands
    s = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", s)
    # Remove special chars
    s = re.sub(r"[{}\-:]", "", s)
    return re.sub(r"[^a-z0-9]", "", s.lower())


def titles_match(t1: str, t2: str) -> bool:
    """Check if titles match."""
    n1, n2 = normalize(t1), normalize(t2)
    if not n1 or not n2:
        return False
    return n1 in n2 or n2 in n1


def is_website(entry: BibEntry) -> bool:
    """Check if entry is a website (no DOI expected)."""
    # arXiv papers are NOT websites
    if entry.is_arxiv or entry.eprint:
        return False
    
    # Has booktitle = conference paper
    if entry.booktitle:
        return False
    
    url = entry.url or entry.howpublished or ""
    
    # Paper repositories are NOT websites
    for pattern in PAPER_REPO_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return False
    
    # Check website patterns
    for pattern in WEBSITE_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    
    # techreport without DOI = probably a website/report
    if entry.entry_type == "techreport" and not entry.doi:
        return True
    
    return False


def get_arxiv_doi(entry: BibEntry) -> Optional[str]:
    """Get arXiv DOI from eprint field."""
    eprint = entry.eprint
    if eprint:
        # Clean the eprint ID
        eprint = eprint.replace("arXiv:", "").replace("arxiv:", "").strip()
        return f"10.48550/arXiv.{eprint}"
    return None


def replace_key(bibtex: str, new_key: str) -> str:
    """Replace citation key in BibTeX."""
    def replacer(match):
        return f"{match.group(1)}{new_key},"
    return re.sub(r"(@\w+\{)[^,]+,", replacer, bibtex, count=1)


def add_access_date(bibtex: str) -> str:
    """Add access date to website entry."""
    access_date = datetime.now().strftime("%Y-%m-%d")
    
    if "accessed" in bibtex.lower():
        return bibtex
    
    if re.search(r"\bnote\s*=\s*\{", bibtex, re.IGNORECASE):
        return re.sub(
            r"(\bnote\s*=\s*\{[^}]*)\}",
            rf"\1, Last accessed: {access_date}}}",
            bibtex,
        )
    else:
        return re.sub(
            r"\n\}$",
            f',\n  note = {{Last accessed: {access_date}}}\n}}',
            bibtex,
        )


def parse_bib_file(bib_path: Path) -> list[BibEntry]:
    """Parse a .bib file into a list of entries."""
    if not bib_path.exists():
        return []
    
    content = bib_path.read_text(encoding="utf-8", errors="replace")
    entries = []
    raw_entries = re.split(r"\n(?=@)", content)
    
    for raw in raw_entries:
        entry = BibEntry.parse(raw)
        if entry:
            entries.append(entry)
    
    return entries


class CitationVerifier:
    """Verifies BibTeX citations against academic databases."""
    
    def __init__(
        self,
        email: Optional[str] = None,
        rate_limit: float = 0.5,
    ):
        """Initialize verifier.
        
        Args:
            email: Email for API access
            rate_limit: Seconds between API requests
        """
        self.email = email
        self.rate_limit = rate_limit
        self._last_request = 0.0
    
    async def _rate_limit_wait(self):
        """Wait to respect rate limits."""
        import time
        
        now = time.time()
        elapsed = now - self._last_request
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        self._last_request = time.time()
    
    async def get_bibtex_from_doi(self, doi: str) -> tuple[str, Optional[str]]:
        """Fetch BibTeX from DOI.
        
        Args:
            doi: DOI string
            
        Returns:
            Tuple of (bibtex, title)
        """
        await self._rate_limit_wait()
        
        try:
            # Try doi.org content negotiation
            url = f"https://doi.org/{urllib.parse.quote(doi, safe='')}"
            headers = {
                "Accept": "application/x-bibtex",
                "User-Agent": "ingestor/1.0 (mailto:research@example.com)",
            }
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                bibtex = response.read().decode("utf-8")
            
            if not bibtex or not bibtex.strip().startswith("@"):
                return "", None
            
            bibtex = bibtex.strip()
            title_match = re.search(r"title\s*=\s*\{([^}]+)\}", bibtex, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else None
            
            return bibtex, title
            
        except Exception:
            return "", None
    
    async def get_bibtex_from_arxiv(
        self,
        arxiv_id: str,
        key: str,
    ) -> tuple[str, Optional[str]]:
        """Fetch BibTeX from arXiv API.
        
        Args:
            arxiv_id: arXiv ID
            key: Citation key to use
            
        Returns:
            Tuple of (bibtex, title)
        """
        await self._rate_limit_wait()
        
        # Clean arxiv ID
        arxiv_id = arxiv_id.replace("arXiv:", "").replace("arxiv:", "").strip()
        
        url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
        headers = {"User-Agent": "ingestor/1.0"}
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                xml_data = response.read().decode()
            
            # Parse XML
            root = ET.fromstring(xml_data)
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom",
            }
            
            entry = root.find("atom:entry", ns)
            if entry is None:
                return "", None
            
            title = entry.find("atom:title", ns)
            title_text = title.text.strip().replace("\n", " ") if title is not None else None
            
            # Get authors
            authors = []
            for author in entry.findall("atom:author", ns):
                name = author.find("atom:name", ns)
                if name is not None:
                    authors.append(name.text.strip())
            
            if not authors or not title_text:
                return "", None
            
            # Get year from published date
            published = entry.find("atom:published", ns)
            year = published.text[:4] if published is not None else str(datetime.now().year)
            
            # Get primary category
            category = entry.find("arxiv:primary_category", ns)
            cat_term = category.get("term") if category is not None else "cs.AI"
            
            # Build BibTeX
            author_str = " and ".join(authors)
            bibtex = f"""@misc{{{key},
  title={{{title_text}}},
  author={{{author_str}}},
  year={{{year}}},
  eprint={{{arxiv_id}}},
  archivePrefix={{arXiv}},
  primaryClass={{{cat_term}}},
  url={{https://arxiv.org/abs/{arxiv_id}}}
}}"""
            return bibtex, title_text
            
        except Exception:
            return "", None
    
    async def search_crossref(
        self,
        title: str,
        author: str = "",
    ) -> list[dict[str, str]]:
        """Search CrossRef for DOI.
        
        Args:
            title: Paper title
            author: Optional author string
            
        Returns:
            List of results with 'doi' and 'title' keys
        """
        await self._rate_limit_wait()
        
        query = re.sub(r"[{}\\]", "", title or "")
        if not query:
            return []
        
        params = {"query.bibliographic": query, "rows": "5"}
        if author:
            first_author = author.split(" and ")[0].split(",")[0].strip()
            params["query.author"] = first_author
        
        url = f"https://api.crossref.org/works?{urllib.parse.urlencode(params)}"
        headers = {"User-Agent": f"ingestor/1.0 (mailto:{self.email or 'research@example.com'})"}
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            return [
                {
                    "doi": item.get("DOI", ""),
                    "title": (item.get("title") or [""])[0],
                }
                for item in data.get("message", {}).get("items", [])
            ]
        except Exception:
            return []
    
    async def verify_entry(
        self,
        entry: BibEntry,
        skip_keys: Optional[set[str]] = None,
    ) -> VerificationResult:
        """Verify a single BibTeX entry.
        
        Args:
            entry: Parsed entry
            skip_keys: Keys to skip verification
            
        Returns:
            VerificationResult
        """
        key = entry.key
        title = entry.title
        author = entry.author
        doi = clean_doi(entry.doi)
        
        # Skip verification for specified keys
        if skip_keys and key in skip_keys:
            return VerificationResult(
                key=key,
                status="manual",
                bibtex=entry.raw,
                message="Manual entry (skipped verification)",
            )
        
        # arXiv papers - fetch from arXiv API
        if entry.is_arxiv and entry.eprint:
            bibtex, arxiv_title = await self.get_bibtex_from_arxiv(entry.eprint, key)
            if bibtex and arxiv_title:
                if titles_match(title or "", arxiv_title):
                    return VerificationResult(
                        key=key,
                        status="arxiv",
                        bibtex=bibtex,
                        message=f"arXiv:{entry.eprint} (verified)",
                    )
                else:
                    return VerificationResult(
                        key=key,
                        status="failed",
                        bibtex=entry.raw,
                        message=f"arXiv title mismatch: '{title[:40] if title else ''}...' vs '{arxiv_title[:40]}...'",
                    )
            return VerificationResult(
                key=key,
                status="failed",
                bibtex=entry.raw,
                message=f"arXiv:{entry.eprint} (API failed)",
            )
        
        # Website - use original with access date
        if is_website(entry):
            bibtex = add_access_date(entry.raw)
            url = entry.url or entry.howpublished or ""
            return VerificationResult(
                key=key,
                status="website",
                bibtex=bibtex,
                message=f"Website: {url[:40] if url else 'no URL'}",
            )
        
        # Try existing DOI
        if doi:
            bibtex, actual_title = await self.get_bibtex_from_doi(doi)
            if bibtex and titles_match(title or "", actual_title or ""):
                return VerificationResult(
                    key=key,
                    status="verified",
                    bibtex=replace_key(bibtex, key),
                    message=f"DOI verified: {doi}",
                )
        
        # Try arXiv DOI
        arxiv_doi = get_arxiv_doi(entry)
        if arxiv_doi:
            bibtex, actual_title = await self.get_bibtex_from_doi(arxiv_doi)
            if bibtex:
                return VerificationResult(
                    key=key,
                    status="arxiv",
                    bibtex=replace_key(bibtex, key),
                    message=f"arXiv DOI: {arxiv_doi}",
                )
        
        # Search CrossRef
        for result in await self.search_crossref(title or "", author or ""):
            if titles_match(title or "", result["title"]):
                bibtex, actual_title = await self.get_bibtex_from_doi(result["doi"])
                if bibtex and titles_match(title or "", actual_title or ""):
                    return VerificationResult(
                        key=key,
                        status="searched",
                        bibtex=replace_key(bibtex, key),
                        message=f"Found: {result['doi']}",
                    )
        
        # Failed
        return VerificationResult(
            key=key,
            status="failed",
            bibtex=entry.raw,
            message="Could not verify",
        )
    
    async def verify_file(
        self,
        input_path: Path,
        output_dir: Path,
        skip_keys: Optional[set[str]] = None,
        manual_path: Optional[Path] = None,
        dry_run: bool = False,
    ) -> tuple[VerificationStats, list[VerificationResult]]:
        """Verify a single BibTeX file.
        
        Args:
            input_path: Input .bib file
            output_dir: Output directory
            skip_keys: Keys to skip verification
            manual_path: Optional manual.bib with pre-verified entries
            dry_run: Don't write files
            
        Returns:
            Tuple of (stats, results)
        """
        verified_bib = output_dir / "verified.bib"
        failed_bib = output_dir / "failed.bib"
        report_file = output_dir / "report.md"
        
        entries = parse_bib_file(input_path)
        manual_entries = []
        if manual_path and manual_path.exists():
            manual_entries = parse_bib_file(manual_path)
        
        stats = VerificationStats()
        verified = []
        failed = []
        
        # Process entries
        for entry in entries:
            result = await self.verify_entry(entry, skip_keys)
            setattr(stats, result.status, getattr(stats, result.status) + 1)
            
            if result.status == "failed":
                failed.append(result)
            else:
                verified.append(result)
        
        # Add manual entries
        for entry in manual_entries:
            result = VerificationResult(
                key=entry.key,
                status="manual",
                bibtex=entry.raw,
                message="Manual entry",
            )
            verified.append(result)
            stats.manual += 1
        
        all_results = verified + failed
        
        if dry_run:
            return stats, all_results
        
        # Write verified.bib
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(verified_bib, "w", encoding="utf-8") as f:
            f.write(f"% Verified Citations\n")
            f.write(f"% Generated: {datetime.now().isoformat()}\n")
            f.write(f"% Total: {len(verified)} entries\n")
            f.write(f"% Source: {input_path.name}\n\n")
            for v in verified:
                f.write(f"% [{v.status}] {v.key}\n")
                f.write(v.bibtex)
                f.write("\n\n")
        
        # Write failed.bib
        with open(failed_bib, "w", encoding="utf-8") as f:
            f.write(f"% Failed Verification - Need Manual Attention\n")
            f.write(f"% Generated: {datetime.now().isoformat()}\n")
            f.write(f"% Total: {len(failed)} entries\n\n")
            for entry in failed:
                f.write(f"% {entry.message}\n")
                f.write(entry.bibtex)
                f.write("\n\n")
        
        # Write report
        self._write_report(report_file, stats, verified, failed, input_path.name)
        
        return stats, all_results
    
    async def verify_directory(
        self,
        input_dir: Path,
        output_dir: Path,
        skip_keys: Optional[set[str]] = None,
        dry_run: bool = False,
    ) -> tuple[VerificationStats, list[VerificationResult]]:
        """Verify all .bib files in a directory.
        
        Args:
            input_dir: Input directory with .bib files
            output_dir: Output directory
            skip_keys: Keys to skip verification
            dry_run: Don't write files
            
        Returns:
            Tuple of (stats, results)
        """
        verified_dir = output_dir / "verified"
        failed_dir = output_dir / "failed"
        report_file = output_dir / "report.md"
        
        if not dry_run:
            verified_dir.mkdir(parents=True, exist_ok=True)
            failed_dir.mkdir(parents=True, exist_ok=True)
        
        bib_files = sorted(input_dir.glob("*.bib"))
        
        stats = VerificationStats()
        all_verified = []
        all_failed = []
        file_results = []
        
        for bib_file in bib_files:
            entries = parse_bib_file(bib_file)
            if not entries:
                continue
            
            file_verified = []
            file_failed = []
            
            for entry in entries:
                result = await self.verify_entry(entry, skip_keys)
                result.source_file = bib_file.name
                setattr(stats, result.status, getattr(stats, result.status) + 1)
                
                if result.status == "failed":
                    file_failed.append(result)
                    all_failed.append(result)
                else:
                    file_verified.append(result)
                    all_verified.append(result)
            
            file_results.append({
                "file": bib_file.name,
                "verified": len(file_verified),
                "failed": len(file_failed),
            })
            
            if dry_run:
                continue
            
            # Write verified entries
            if file_verified:
                out_file = verified_dir / bib_file.name
                with open(out_file, "w", encoding="utf-8") as f:
                    f.write(f"% Verified Citations from {bib_file.name}\n")
                    f.write(f"% Generated: {datetime.now().isoformat()}\n\n")
                    for v in file_verified:
                        f.write(f"% [{v.status}] {v.key}\n")
                        f.write(v.bibtex)
                        f.write("\n\n")
            
            # Write failed entries
            if file_failed:
                out_file = failed_dir / bib_file.name
                with open(out_file, "w", encoding="utf-8") as f:
                    f.write(f"% Failed Verification from {bib_file.name}\n")
                    f.write(f"% Generated: {datetime.now().isoformat()}\n\n")
                    for entry in file_failed:
                        f.write(f"% {entry.message}\n")
                        f.write(entry.bibtex)
                        f.write("\n\n")
        
        if not dry_run:
            self._write_directory_report(
                report_file, stats, all_verified, all_failed, file_results, input_dir.name
            )
        
        return stats, all_verified + all_failed
    
    def _write_report(
        self,
        report_file: Path,
        stats: VerificationStats,
        verified: list[VerificationResult],
        failed: list[VerificationResult],
        source_name: str,
    ):
        """Write markdown report for single file mode."""
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# Citation Verification Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Source: {source_name}\n\n")
            f.write("## Summary\n\n")
            f.write("| Status | Count |\n|--------|-------|\n")
            f.write(f"| verified | {stats.verified} |\n")
            f.write(f"| arxiv | {stats.arxiv} |\n")
            f.write(f"| searched | {stats.searched} |\n")
            f.write(f"| website | {stats.website} |\n")
            f.write(f"| manual | {stats.manual} |\n")
            f.write(f"| failed | {stats.failed} |\n")
            f.write(f"| **Total Verified** | **{stats.total_verified}** |\n")
            f.write(f"| **Total Failed** | **{stats.failed}** |\n\n")
            
            if failed:
                f.write("## Failed Entries\n\n")
                for entry in failed:
                    f.write(f"- `{entry.key}`: {entry.message}\n")
    
    def _write_directory_report(
        self,
        report_file: Path,
        stats: VerificationStats,
        all_verified: list[VerificationResult],
        all_failed: list[VerificationResult],
        file_results: list[dict],
        source_dir: str,
    ):
        """Write markdown report for directory mode."""
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# Citation Verification Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Source directory: {source_dir}\n")
            f.write(f"Files processed: {len(file_results)}\n\n")
            
            f.write("## Summary\n\n")
            f.write("| Status | Count |\n|--------|-------|\n")
            f.write(f"| verified | {stats.verified} |\n")
            f.write(f"| arxiv | {stats.arxiv} |\n")
            f.write(f"| searched | {stats.searched} |\n")
            f.write(f"| website | {stats.website} |\n")
            f.write(f"| manual | {stats.manual} |\n")
            f.write(f"| failed | {stats.failed} |\n")
            f.write(f"| **Total Verified** | **{stats.total_verified}** |\n")
            f.write(f"| **Total Failed** | **{stats.failed}** |\n\n")
            
            f.write("## Files\n\n")
            f.write("| File | Verified | Failed |\n|------|----------|--------|\n")
            for fr in file_results:
                f.write(f"| {fr['file']} | {fr['verified']} | {fr['failed']} |\n")
            f.write("\n")
            
            if all_failed:
                f.write("## Failed Entries\n\n")
                for entry in all_failed:
                    f.write(f"- `{entry.key}` ({entry.source_file}): {entry.message}\n")
