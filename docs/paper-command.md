# Paper Command Documentation

The `paper` command downloads academic papers with full metadata extraction, markdown conversion, and BibTeX generation.

## Features

- **Multiple Input Formats**: DOI, arXiv ID, Semantic Scholar URL, PDF URLs, paper titles
- **PDF Download**: Downloads paper PDF from available sources
- **Markdown Extraction**: Converts PDF to markdown with YAML metadata header
- **BibTeX Generation**: Creates citation file for reference managers
- **Citation Graph**: Fetches paper references via Semantic Scholar API

## Input Formats

| Format | Example |
|--------|---------|
| DOI | `10.1038/nature12373` |
| DOI URL | `https://doi.org/10.1038/nature12373` |
| arXiv ID | `arXiv:1706.03762` or `1706.03762` |
| arXiv URL | `https://arxiv.org/abs/1706.03762` |
| Semantic Scholar URL | `https://www.semanticscholar.org/paper/...` |
| Semantic Scholar ID | 40-character hex string |
| OpenAlex ID | `W2741809807` |
| PubMed ID | `PMID:12345678` |
| PMC ID | `PMC1234567` |
| Direct PDF URL | `https://example.com/paper.pdf` |
| Paper title | `"Attention Is All You Need"` |

## Output Files

| File | Description |
|------|-------------|
| `Author_Year_Title.pdf` | Downloaded PDF |
| `Author_Year_Title.md` | Extracted markdown with metadata header |
| `citation.bib` | BibTeX citation |
| `references.txt` | Citation references (with `--references`) |

## Usage

```bash
# Basic usage with DOI
ingestor paper 10.1038/nature12373

# arXiv paper with references
ingestor paper arXiv:1706.03762 --references

# Custom output directory
ingestor paper "Attention Is All You Need" -o ./papers

# Skip markdown extraction (PDF + BibTeX only)
ingestor paper 10.1038/nature12373 --no-markdown

# Skip BibTeX generation
ingestor paper arXiv:1706.03762 --no-bibtex
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `-o, --output` | `./output` | Output directory |
| `--email` | env: `INGESTOR_EMAIL` | Email for API access (CrossRef, Unpaywall) |
| `--s2-key` | env: `S2_API_KEY` | Semantic Scholar API key |
| `--bibtex/--no-bibtex` | `--bibtex` | Generate BibTeX citation |
| `--markdown/--no-markdown` | `--markdown` | Extract PDF to markdown |
| `--references` | off | Fetch citation references |
| `--max-refs` | 50 | Maximum references to fetch |
| `-v, --verbose` | off | Verbose output |

## Example Output

### Command
```bash
ingestor paper arXiv:1706.03762 -o output/paper_test --references
```

### Output Files
```
output/paper_test/
├── Vaswani_2017_Attention_Is_All_You_Need.pdf  (2.2 MB)
├── Vaswani_2017_Attention_Is_All_You_Need.md   (51 KB)
└── citation.bib                                (1.5 KB)
```

### Markdown Header
```yaml
---
title: "Attention Is All You Need"
authors: ['Ashish Vaswani', 'Noam Shazeer', 'Niki Parmar', 'Jakob Uszkoreit', 'Llion Jones', 'Aidan N. Gomez', 'Lukasz Kaiser', 'Illia Polosukhin']
year: 2017
doi: "10.48550/arXiv.1706.03762"
arxiv: "1706.03762"
abstract: "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks..."
source_pdf: "Vaswani_2017_Attention_Is_All_You_Need.pdf"
---
```

### BibTeX Entry
```bibtex
@article{vaswani2017attention,
  title = {Attention Is All You Need},
  author = {Vaswani, Ashish and Shazeer, Noam and Parmar, Niki and Uszkoreit, Jakob and Jones, Llion and Gomez, Aidan N. and Kaiser, Lukasz and Polosukhin, Illia},
  year = {2017},
  doi = {10.48550/arXiv.1706.03762},
  eprint = {1706.03762},
  archiveprefix = {arXiv},
  primaryclass = {cs.CL}
}
```

## API Clients

The paper command uses multiple APIs to fetch metadata and PDFs:

| API | Purpose |
|-----|---------|
| Semantic Scholar | Metadata, citations, references |
| CrossRef | DOI resolution, metadata |
| OpenAlex | Metadata, open access links |
| arXiv | arXiv papers, metadata |
| Unpaywall | Open access PDF links |
| PubMed/PMC | Biomedical papers |

## Environment Variables

```bash
export INGESTOR_EMAIL="your@email.com"  # Required for CrossRef/Unpaywall
export S2_API_KEY="your-api-key"        # Optional: Higher rate limits
```

## Related Commands

- `ingestor ingest <file>` - Convert any file to markdown
- `ingestor paper-meta <identifier>` - Get metadata only (no download)
- `ingestor paper-batch <file>` - Batch download papers from list
