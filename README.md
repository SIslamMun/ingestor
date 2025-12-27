# Ingestor

> Universal document → markdown + images converter  
> With integrated scientific paper acquisition and AI-powered deep research

**Three CLI Tools:**
- `ingestor` - Extract markdown and images from PDFs, Word docs, PowerPoints, EPUBs, spreadsheets, web pages, YouTube videos, audio files, Git repos, and more
- `parser` - Download and process scientific papers from DOI, arXiv, or other identifiers with BibTeX generation and citation verification
- `researcher` - AI-powered deep research using Google Gemini

Uses Google Magika file detection.

## Supported Formats

| Format | Extensions | Notes |
|--------|-----------|-------|
| PDF | .pdf ✅ | Docling ML extraction, academic papers, tables |
| Text | .txt ✅  .md ✅  .rst ✅ | With charset detection |
| Word | .docx ✅ | Extracts images |
| PowerPoint | .pptx ✅ | Slides + images |
| EPUB | .epub ✅ | Chapters + images |
| Excel | .xlsx ✅  .xls 🟡 | All sheets as tables |
| CSV | .csv ✅ | Auto-delimiter detection |
| JSON | .json ✅ | Objects and arrays |
| XML | .xml ✅ | Secure parsing |
| Images | .png ✅  .jpg ✅  .gif 🟡  .webp 🟡 | EXIF metadata |
| Audio | .wav ✅  .mp3 🟡  .flac 🟡 | Whisper transcription |
| Web | URLs ✅ | Deep crawling (Crawl4AI) |
| YouTube | Videos ✅  Playlists ✅ | Transcripts |
| Git/GitHub | URLs ✅ | Clone, API, SSH, submodules |
| Archives | .zip ✅ | Recursive extraction |

✅ = tested with real files
🟡 = same extractor, untested extension

## Quick Start

```bash
# Install with all formats
uv sync --extra all-formats

# Convert a file
ingestor ingest document.docx -o ./output

# Process a folder
ingestor batch ./documents -o ./output
```

## Installation

**Core only** (text, JSON, images):
```bash
uv sync
```

**Specific formats**:
```bash
uv sync --extra pdf         # PDF documents (Docling ML)
uv sync --extra paper       # Scientific papers (DOI, arXiv + PDF)
uv sync --extra docx        # Word documents
uv sync --extra xlsx        # Excel files
uv sync --extra web         # Web crawling
uv sync --extra youtube     # YouTube transcripts
uv sync --extra git         # Git/GitHub repositories
uv sync --extra audio       # Audio transcription
```

**Multiple formats**:
```bash
uv sync --extra docx --extra xlsx --extra web
```

**All formats** (recommended):
```bash
uv sync --extra all-formats
```

**Everything** (including AI features):
```bash
uv sync --all-extras
```

## Usage

### Single File
```bash
ingestor ingest document.pdf
ingestor ingest spreadsheet.xlsx -o ./output
ingestor ingest "https://example.com" -o ./crawled
```

### Batch Processing
```bash
ingestor batch ./documents -o ./output
ingestor batch ./docs --recursive --concurrency 10
```

### PDF Documents

The PDF extractor uses **Docling** (ML-based) for high-quality extraction with PyMuPDF fallback for OCR.

```bash
# Basic PDF extraction
ingestor ingest paper.pdf -o ./output

# Batch process PDFs
ingestor batch ./papers -o ./output
```

#### Features

- **Structure Preservation**: Multi-column layouts, headings, paragraphs
- **Academic Papers**: Linked citations, reference anchors, section detection
- **Figure Extraction**: Automatic embedding at captions, logo filtering
- **Table Extraction**: Tables converted to markdown
- **LaTeX Equations**: Extracted as `$$...$$` display math blocks via Docling's formula enrichment
- **OCR Fallback**: Scanned PDFs via PyMuPDF

#### Output Structure
```
output/paper/
├── paper.md              # Processed markdown
└── img/
    ├── figure1.png       # Extracted figures
    ├── figure2.png
    └── ...
```

#### Post-Processing (Academic Papers)

The extractor automatically applies:
- **Citation linking**: `[7]` → `[[7]](#ref-7)` with anchor links
- **Citation range expansion**: `[3]-[5]` → `[[3]](#ref-3), [[4]](#ref-4), [[5]](#ref-5)`
- **Section detection**: Numbered sections (1., 1.1, 1.1.1) become proper headers
- **Figure embedding**: Figures inserted above their captions
- **LaTeX equations**: Extracted as `$$...$$` display math blocks
- **Ligature normalization**: ﬁ→fi, ﬂ→fl, etc.

#### Requirements

```bash
# Install PDF support
uv sync --extra pdf

# Docling downloads ~500MB of ML models on first use
```

### Scientific Papers

Retrieve scientific papers from DOI, arXiv, title search, or direct URLs with multi-source fallback.

> **Note:** Scientific paper commands use the `parser` CLI tool.

**Features:**
- Multi-source paper retrieval (arXiv, Semantic Scholar, OpenAlex, PMC, Unpaywall, bioRxiv)
- DOI and arXiv ID resolution
- Title-based paper search
- Direct PDF URL support
- BibTeX/metadata extraction
- DOI to BibTeX conversion (`doi2bib`)
- Citation verification (`verify`)
- Skip existing / force re-download

**Input Formats:**
- DOI: `10.1038/nature12373` or `-d "10.1038/nature12373"`
- arXiv ID: `arXiv:1706.03762` or `2301.12345`
- Title search: `-t "Attention Is All You Need"`
- Direct PDF URLs: `https://arxiv.org/pdf/1706.03762.pdf`
- Semantic Scholar URL

**Output:**
- Downloaded PDF
- Log file with retrieval details

```bash
# Install paper support (includes PDF extraction)
uv sync --extra paper

# Basic paper retrieval by DOI
parser retrieve --doi "10.1038/nature12373"
parser retrieve -d "10.1038/nature12373"

# arXiv papers
parser retrieve arXiv:1706.03762
parser retrieve 2301.12345
parser retrieve https://arxiv.org/abs/1706.03762

# Search by title
parser retrieve --title "Attention Is All You Need"
parser retrieve -t "Deep Residual Learning for Image Recognition"

# Direct PDF URL
parser retrieve "https://arxiv.org/pdf/1706.03762.pdf"

# With output directory and email for API access
parser retrieve -d "10.1038/nature12373" -o ./papers -e your@email.com

# Skip if already downloaded (default), or force re-download
parser retrieve -t "BERT" --no-skip-existing
```

#### DOI to BibTeX (doi2bib)

Convert DOI or arXiv identifiers to BibTeX citations (like the original [doi2bib](https://github.com/davidagraf/doi2bib) tool):

```bash
# Single DOI to BibTeX (prints to stdout)
parser doi2bib 10.1038/s41586-020-2649-2

# arXiv ID
parser doi2bib arXiv:1706.03762

# Save to file
parser doi2bib 10.1038/nature12373 -o numpy.bib

# Different output formats
parser doi2bib 10.1038/nature12373 --format json
parser doi2bib 10.1038/nature12373 --format markdown

# Process multiple identifiers from a file
parser doi2bib -i dois.txt -o citations/

# With Semantic Scholar API key (for better metadata)
parser doi2bib 10.1038/nature12373 --s2-key YOUR_API_KEY
```

**Input file format (one per line):**
```
10.1038/s41586-020-2649-2
arXiv:1706.03762
10.1126/science.1234567
# Comments are ignored
```

**Output formats:**
- `bibtex` (default): Standard BibTeX format
- `json`: Full metadata as JSON
- `markdown`: Formatted citation text

#### Output Example

```bash
parser retrieve -t \"Attention Is All You Need\" -o output/papers
```

```
output/papers/
├── Attention_Is_All_You_Need.pdf   # Downloaded PDF
└── Attention Is All You Need.log   # Retrieval log with source info
```

**Retrieval sources (tried in order):**
1. Unpaywall (requires email)
2. arXiv (preprints)
3. PMC (PubMed Central)
4. bioRxiv/medRxiv (preprints)
5. Semantic Scholar
6. OpenAlex
7. Web search

#### Batch Paper Processing

Process multiple papers from a file (CSV, JSON, or TXT):

```bash
# From CSV with 'doi' and/or 'title' columns
parser batch papers.csv -o ./output

# From JSON array
parser batch references.json --concurrency 5

# From TXT (one identifier per line)
parser batch dois.txt -o ./papers
```

**CSV format:**
```csv
doi,title
10.1038/nature12373,"The paper title (optional)"
10.1126/science.1234567,
,Attention Is All You Need
```

**JSON format:**
```json
[
  {"doi": "10.1038/nature12373"},
  {"title": "Attention Is All You Need"},
  {"doi": "10.1126/science.1234567", "title": "Optional title"}
]
```

**TXT format:**
```
# Comments supported
10.1038/nature12373
arXiv:1706.03762
Attention Is All You Need
```

#### Citation Verification

Verify BibTeX citations against academic databases (CrossRef, arXiv):

```bash
# Verify a single .bib file
parser verify references.bib -o ./verified

# Verify a directory of .bib files
parser verify ./citations -o ./output

# With manual pre-verified entries
parser verify refs.bib --manual custom.bib

# Skip specific citation keys
parser verify refs.bib --skip website1 --skip github2

# Dry run (see what would happen)
parser verify refs.bib --dry-run -v
```

**Output structure:**
```
verified/
├── verified.bib     # Successfully verified citations
├── failed.bib       # Citations needing manual attention
└── report.md        # Summary report
```

**Verification logic:**
- DOI citations: Verified against CrossRef/doi.org
- arXiv papers: Verified against arXiv API (title matching)
- Websites: Annotated with access dates (no DOI expected)
- Missing DOIs: Searched via CrossRef title search
- Citation keys: Preserved from original entries

#### Check Paper Sources

See available sources and their status:

```bash
parser sources
```

Output:
```
Paper Acquisition Sources
============================================================

| Source           | Status | Description          | Auth |
|------------------|--------|----------------------|------|
| arXiv            | ✓      | Open access preprints| No auth required |
| Unpaywall        | ✓      | Open access papers   | Email: ✓ |
| PMC              | ✓      | PubMed Central       | NCBI key: ○ Optional |
| bioRxiv          | ✓      | Biology preprints    | No auth required |
| medRxiv          | ✓      | Medical preprints    | No auth required |
| CrossRef         | ✓      | DOI metadata         | Polite pool: ✓ |
| Semantic Scholar | ✓      | Metadata & citations | API key: ○ Optional |
| OpenAlex         | ✓      | Metadata             | Email: ✓ |
| Institutional    | ○      | EZProxy/VPN access   | Run: parser auth |
| WebSearch        | ○      | Claude SDK search    | pip install claude-code-sdk |

Not Implemented (Legal Concerns):
  ⛔ Sci-Hub - PDF retrieval (intentionally excluded)
  ⛔ LibGen  - PDF retrieval (intentionally excluded)
```

#### Institutional Access (EZProxy/VPN)

Access papers through your university's subscriptions (IEEE, ACM, Elsevier, etc.):

```bash
# EZProxy mode - opens browser for Shibboleth/SAML login
parser auth --proxy-url "https://ezproxy.university.edu/login?url="

# VPN mode - runs your VPN connection script
parser auth --vpn-script ~/vpn-connect.sh
```

**Environment variables:**
```bash
export INSTITUTIONAL_PROXY_URL="https://ezproxy.university.edu/login?url="
export INSTITUTIONAL_VPN_SCRIPT="/path/to/vpn-connect.sh"
```

**Requirements for EZProxy:**
```bash
pip install selenium webdriver-manager
```

#### Config Sync (Push/Pull)

Sync your paper acquisition config across machines using GitHub Gists:

```bash
# Create config file
parser init

# Push config to a private gist
parser config-push

# Pull config on another machine
parser config-pull --gist-id abc123def456
```

**Requirements:**
```bash
# Install GitHub CLI
# macOS: brew install gh
# Linux: see https://cli.github.com/
gh auth login
```

#### Supported Identifiers

| Type | Examples |
|------|----------|
| DOI | `10.1038/nature12373`, `https://doi.org/10.1038/nature12373` |
| arXiv | `arXiv:1706.03762`, `2301.12345`, `https://arxiv.org/abs/1706.03762` |
| Semantic Scholar | `https://www.semanticscholar.org/paper/...` |
| OpenAlex | `W2741809807`, `https://openalex.org/W2741809807` |
| PubMed | `PMID:12345678`, `https://pubmed.ncbi.nlm.nih.gov/12345678` |
| PMC | `PMC1234567` |
| PDF URL | `https://example.com/paper.pdf` |
| Title | `"Attention Is All You Need"` |

#### Features

- **DOI Resolution**: Automatic resolution via CrossRef, Semantic Scholar, OpenAlex
- **arXiv Support**: Full arXiv ID resolution and PDF download
- **PDF Download**: Open access PDFs via Unpaywall, arXiv, PMC, bioRxiv
- **Markdown Extraction**: PDF to markdown with YAML metadata header
- **BibTeX Generation**: Automatic citation generation with proper formatting
- **Citation Graph**: Fetch cited papers via Semantic Scholar API (`--references`)
- **Metadata Enrichment**: Authors, year, venue, abstract, citation count
- **Citation Verification**: Verify BibTeX entries against CrossRef/arXiv (doi2bib-style)
- **Batch Processing**: Process multiple papers from CSV/JSON/TXT files

#### API Clients

| API | Purpose |
|-----|---------|
| Semantic Scholar | Metadata, citations, references |
| CrossRef | DOI resolution, metadata |
| OpenAlex | Metadata, open access links |
| arXiv | arXiv papers, metadata |
| Unpaywall | Open access PDF links |
| PubMed/PMC | Biomedical papers |
| bioRxiv/medRxiv | Biology and medical preprints |

#### Environment Variables

```bash
# Email for API access (CrossRef polite pool, Unpaywall, OpenAlex)
export INGESTOR_EMAIL="your@email.com"

# Semantic Scholar API key (optional, for higher rate limits)
export S2_API_KEY="your_api_key"

# NCBI API key for PubMed Central (optional)
export NCBI_API_KEY="your_ncbi_key"

# Institutional access (optional)
export INSTITUTIONAL_PROXY_URL="https://ezproxy.university.edu/login?url="
export INSTITUTIONAL_VPN_SCRIPT="/path/to/vpn-connect.sh"
```

#### Output Structure

```
output/
├── Author_Year_Title.pdf     # Downloaded PDF
├── Author_Year_Title.md      # Markdown with YAML metadata header
├── citation.bib              # BibTeX citation
└── references.txt            # Citation list (with --references)
```

#### Markdown Output Format

```markdown
---
title: "Paper Title"
authors: ['Author One', 'Author Two']
year: 2023
doi: "10.1038/nature12373"
arxiv: "2301.12345"
venue: "Nature"
abstract: "Paper abstract text..."
source_pdf: "Author_2023_Paper_Title.pdf"
---

## Paper Title

Author One, Author Two

## Abstract

Paper abstract text...

---

## Content

Full paper content extracted from PDF...
```

### Deep Research

> **Note:** Deep research commands use the `researcher` CLI tool.

AI-powered deep research using Google Gemini to conduct comprehensive research on any topic.

```bash
# Install research support
uv sync --extra researcher

# Conduct deep research on a topic
researcher research "quantum computing applications in drug discovery"

# With custom output directory
researcher research "machine learning for climate modeling" -o ./research_output

# With verbose output
researcher research "renewable energy storage solutions" -v
```

**Requirements:**
- Google Gemini API key (`GOOGLE_API_KEY` environment variable)
- `uv sync --extra researcher`

**Output:**
- Comprehensive research report in markdown format
- Structured analysis with citations and sources

### Web Crawling
```bash
ingestor crawl https://docs.example.com --max-depth 3 --max-pages 100
ingestor crawl https://example.com --strategy dfs --include "/blog/*"
```

### YouTube
```bash
ingestor ingest "https://youtube.com/watch?v=..."
ingestor ingest "https://youtube.com/playlist?list=..." --playlist
```

### Git Repositories

The unified Git extractor supports both GitHub API access (for specific files/directories) and full git clone (for any server).

#### Quick Access via GitHub API
```bash
# Extract entire repository (README, metadata, key files)
ingestor ingest "https://github.com/owner/repo" -o ./output

# Extract a specific file
ingestor ingest "https://github.com/owner/repo/blob/main/src/file.py" -o ./output

# Extract a directory
ingestor ingest "https://github.com/owner/repo/tree/main/src" -o ./output
```

#### Full Repository Clone
```bash
# Clone and process entire repository (shallow clone by default)
ingestor clone https://github.com/owner/repo -o ./output

# Clone specific branch
ingestor clone https://github.com/owner/repo --branch develop

# Clone specific tag
ingestor clone https://github.com/owner/repo --tag v1.0.0

# Full clone (all history)
ingestor clone https://github.com/owner/repo --full

# Clone private repository (SSH) - works with any git server
ingestor clone git@github.com:owner/private-repo.git
ingestor clone git@gitlab.com:owner/repo.git
ingestor clone git@bitbucket.org:owner/repo.git

# Clone with token (for HTTPS private repos)
ingestor clone https://github.com/owner/private-repo --token $GITHUB_TOKEN

# Clone with submodules
ingestor clone https://github.com/owner/repo --submodules

# Limit files processed
ingestor clone https://github.com/owner/repo --max-files 100 --max-file-size 100000
```

#### Private Repository Authentication

For **SSH URLs** (`git@github.com:...`), authentication uses your SSH keys automatically.

For **HTTPS URLs** with private repositories, use the `--token` flag:

```bash
# Using GitHub Personal Access Token (PAT)
export GITHUB_TOKEN="ghp_your_token_here"
ingestor clone https://github.com/owner/private-repo --token $GITHUB_TOKEN

# Or inline
ingestor clone https://github.com/owner/private-repo --token "ghp_your_token"
```

**How it works:** The token is injected into the HTTPS URL for authentication:
- Original: `https://github.com/owner/repo`
- With token: `https://<token>@github.com/owner/repo`

**Token Requirements:**
- GitHub: Create a [Personal Access Token](https://github.com/settings/tokens) with `repo` scope
- GitLab: Create a [Project Access Token](https://docs.gitlab.com/ee/user/project/settings/project_access_tokens.html)
- Bitbucket: Create an [App Password](https://support.atlassian.com/bitbucket-cloud/docs/app-passwords/)

**Security Note:** Tokens are automatically redacted from error messages to prevent accidental exposure.

#### Bulk Repository Cloning (.download_git files)

Create a `.download_git` file with repository URLs (one per line):

```
# repos.download_git
https://github.com/pallets/flask
https://github.com/psf/requests
git@github.com:user/private-repo.git
```

Then process all repositories:
```bash
ingestor clone repos.download_git -o ./output
```

#### Clone Output Structure
```
output/
├── repo_name/
│   ├── repo_name.md       # Combined markdown with all files
│   └── img/               # Extracted images (if any)
```

## Output Structure

```
output/
├── document_name/
│   ├── document_name.md      # Extracted markdown
│   ├── img/
│   │   ├── figure_001.png    # Extracted images (PNG by default)
│   │   └── figure_002.png
│   └── metadata.json         # Optional metadata
```

## Options

| Flag | Description |
|------|-------------|
| `-o, --output` | Output directory (default: ./output) |
| `--keep-raw` | Keep original image formats (don't convert to PNG) |
| `--metadata` | Generate metadata.json files |
| `-v, --verbose` | Verbose output |

## Optional AI Features

### Image Descriptions (requires Ollama)
```bash
uv sync --extra vlm
ingestor ingest document.pptx --describe
```

Generates natural language descriptions for each extracted image using a local VLM.

### Content Cleanup (requires Claude Code SDK)
```bash
uv sync --extra agent
ingestor ingest messy.html --agent
```

Uses Claude to clean up and improve extracted markdown.

## Configuration

Create `ingestor.yaml` in your project or use `--config`:

```yaml
images:
  convert_to_png: true
  target_format: png

web:
  strategy: bfs
  max_depth: 2
  max_pages: 50
  same_domain: true

youtube:
  caption_type: auto
  languages: [en]

audio:
  whisper_model: turbo

output:
  generate_metadata: false
```

## Development

### Setup
```bash
git clone <repo>
cd ingestor
uv sync --extra dev --extra all-formats
```

### Test Setup

**1. Generate test fixtures** (creates sample files for testing):
```bash
uv run python -m tests.fixtures.generate_fixtures
```

**2. Install Playwright browsers** (required for web crawling tests):
```bash
uv run playwright install chromium
```

### Run Tests
```bash
# All tests (run fixture generation first!)
uv run pytest

# Unit tests only (fast, no network)
uv run pytest tests/unit -v

# With network tests (web crawling, YouTube)
uv run pytest --network

# Skip audio tests (slow due to Whisper model loading)
uv run pytest -m "not skip_audio"

# With coverage
uv run pytest --cov=ingestor
```

### Test Categories

The test suite includes 268+ tests across several categories:

| Category | Description | Count |
|----------|-------------|-------|
| **Unit Tests** | Core functionality | 175+ |
| - Edge Cases | Empty files, unicode, malformed data | 30 |
| - Performance | Speed benchmarks, memory tests | 19 |
| - Reference | Regression tests with known outputs | 11 |
| **Integration** | Real file extraction | 93+ |

**Note:** Web crawling uses [Crawl4AI](https://github.com/unclecode/crawl4ai) which requires Playwright browsers. If you skip the `playwright install` step, web tests will be skipped with a helpful message.

### Adding an Extractor

1. Create `src/ingestor/extractors/myformat/myformat_extractor.py`
2. Inherit from `BaseExtractor`
3. Implement `extract()` and `supports()`
4. Register in `core/registry.py`

```python
from ingestor.extractors.base import BaseExtractor
from ingestor.types import ExtractionResult, MediaType

class MyExtractor(BaseExtractor):
    media_type = MediaType.MYFORMAT

    async def extract(self, source):
        # Your extraction logic
        return ExtractionResult(
            markdown="# Extracted Content",
            source=str(source),
            media_type=self.media_type,
        )

    def supports(self, source):
        return str(source).endswith(".myformat")
```

## Architecture

### Processing Flow

```
Input (file/URL)
    │
    ▼
┌─────────────────┐
│  FileDetector   │ ← Uses Magika for AI-powered file type detection (99% accuracy)
│  (Magika)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Router       │ ← Matches detected type to registered extractor
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Extractor     │ ← Format-specific extraction (text + images)
│  (per format)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ImageConverter  │ ← Standardizes images to PNG (optional)
│    (Pillow)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  OutputWriter   │ ← Writes markdown + images to disk
└─────────────────┘
```

### Core Infrastructure

| Library | Purpose |
|---------|---------|
| [magika](https://github.com/google/magika) | AI-powered file type detection by Google (99% accuracy on 100+ types) |
| [charset_normalizer](https://github.com/Ousret/charset_normalizer) | Automatic charset detection for non-UTF8 text files |
| [markdownify](https://github.com/matthewwithanm/python-markdownify) | HTML→Markdown conversion (used internally by DOCX/EPUB/Web extractors) |
| [Pillow](https://github.com/python-pillow/Pillow) | Image processing and format conversion |

### Libraries by Format

| Format | Library | Links |
|--------|---------|-------|
| PDF (.pdf) | docling + pymupdf | [docling](https://github.com/DS4SD/docling), [PyMuPDF](https://github.com/pymupdf/PyMuPDF) |
| Text (.txt, .md, .rst) | charset_normalizer | [charset-normalizer](https://pypi.org/project/charset-normalizer/) |
| Word (.docx) | docx2python + mammoth | [docx2python](https://github.com/ShayHill/docx2python), [mammoth](https://github.com/mwilliamson/python-mammoth) |
| PowerPoint (.pptx) | python-pptx | [GitHub](https://github.com/scanny/python-pptx) |
| EPUB (.epub) | ebooklib | [GitHub](https://github.com/aerkalov/ebooklib) |
| Excel (.xlsx) | pandas + openpyxl | [openpyxl](https://openpyxl.readthedocs.io/) |
| Excel (.xls) | pandas + xlrd | [xlrd](https://github.com/python-excel/xlrd) |
| CSV (.csv) | pandas | [pandas](https://pandas.pydata.org/) |
| JSON (.json) | built-in | - |
| XML (.xml) | defusedxml | [GitHub](https://github.com/tiran/defusedxml) |
| Images (.png, .jpg) | Pillow | [Pillow](https://pillow.readthedocs.io/) |
| Audio (.mp3, .wav) | openai-whisper | [GitHub](https://github.com/openai/whisper) |
| Web (URLs) | crawl4ai | [GitHub](https://github.com/unclecode/crawl4ai) |
| YouTube | yt-dlp + youtube-transcript-api | [yt-dlp](https://github.com/yt-dlp/yt-dlp), [transcript-api](https://github.com/jdepoix/youtube-transcript-api) |
| Git/GitHub | httpx + subprocess | GitHub API + git clone |
| Archives (.zip) | zipfile (built-in) | - |

### How Detection Works

1. **Magika Analysis**: When you pass a file, Magika analyzes the content (not just extension) using a neural network trained on 100+ file types
2. **URL Detection**: URLs are pattern-matched for YouTube vs general web
3. **Fallback**: If Magika fails, extension-based detection is used
4. **Registry Lookup**: Detected `MediaType` is matched to a registered extractor

### Image Extraction

Images are extracted by default from all formats that contain them (DOCX, PPTX, EPUB, Web, ZIP). By default, all images are converted to PNG for consistency. Use `--keep-raw` to preserve original formats.

## License

MIT
