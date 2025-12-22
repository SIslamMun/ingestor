# Ingestor

Convert a variety of data formats to markdown for RAG or LLM training.

Extracts multi-modality format, targetting text, images (also extracted, as much as possible, from provided files) and audio. 

Uses Google Magika file detection.

## Supported Formats

| Format | Extensions | Notes |
|--------|-----------|-------|
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
