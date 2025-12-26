# Complete Pipeline: Research → Parse → Paper → Ingest

This document describes the full knowledge ingestion pipeline using the `ingestor` CLI.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  1. RESEARCH                                                     │
│     ingestor research "query" -o ./output                       │
│     → research_report.md (with arXiv IDs, DOIs)                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. PARSE REFERENCES                                            │
│     ingestor parse-refs research_report.md                      │
│     → references.json (structured)                              │
│     → references.md (human-readable)                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. DOWNLOAD PAPERS                                             │
│     ingestor paper "arXiv:XXXX.XXXXX" -o ./papers               │
│     → Author_Year_Title.pdf                                     │
│     → citation.bib                                              │
│     → references.txt                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. INGEST PDF TO MARKDOWN                                      │
│     ingestor ingest paper.pdf -o ./ingested                     │
│     → paper.md (full markdown)                                  │
│     → img/ (extracted images)                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step 1: Research (Gemini Deep Research)

Use the Gemini Deep Research agent to research a topic and find relevant papers with their identifiers.

```bash
GOOGLE_API_KEY=<your-api-key> uv run ingestor research "What is RAG (Retrieval Augmented Generation)? Find the key papers with their arXiv IDs." -o /tmp/pipeline_test
```

**Output:**
```
Research completed!
Duration: 261.6s
Report saved to: /tmp/pipeline_test/research/research_report.md
```

**Generated files:**
```
/tmp/pipeline_test/research/
├── research_report.md      # Full research report with arXiv IDs
└── research_metadata.json  # Metadata
```

---

## Step 2: Parse References

Extract structured references (arXiv IDs, GitHub repos, DOIs, etc.) from the research report.

```bash
uv run ingestor parse-refs /tmp/pipeline_test/research/research_report.md
```

**Output:**
```
✓ Extracted 26 references:

  • github: 7
  • arxiv: 15
  • paper: 1
  • youtube: 1
  • book: 1
  • website: 1

Output files:
  📄 /tmp/pipeline_test/research/references.md
  📋 /tmp/pipeline_test/research/references.json
```

**Generated files:**
```
/tmp/pipeline_test/research/
├── references.md    # Human-readable reference list
└── references.json  # Structured JSON for programmatic use
```

**Sample `references.md`:**
```markdown
## arXiv Papers (15)

- [2005.11401](https://arxiv.org/abs/2005.11401)  # Original RAG paper
- [2404.16130](https://arxiv.org/abs/2404.16130)  # GraphRAG
- [2310.11511](https://arxiv.org/abs/2310.11511)  # Self-RAG
...

## GitHub Repositories (7)

- [facebookresearch/RAG](https://github.com/facebookresearch/RAG)
- [microsoft/graphrag](https://github.com/microsoft/graphrag)
...
```

---

## Step 3: Download Papers

Download papers using their arXiv IDs, DOIs, or titles. This generates PDF, BibTeX, and references.

```bash
uv run ingestor paper "arXiv:2310.11511" -o /tmp/paper_test
```

**Output:**
```
Processing paper: arXiv:2310.11511

Success! PDF downloaded
  PDF: /tmp/paper_test/Asai_2023_Self-RAG_Learning_to_Retrieve_Generate_and_Critiqu.pdf
  Title: Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection
  Authors: Akari Asai, Zeqiu Wu, Yizhong Wang, et al.
  Year: 2023
  DOI: 10.48550/arXiv.2310.11511
  arXiv: 2310.11511
  BibTeX: /tmp/paper_test/citation.bib
  References: /tmp/paper_test/references.txt (50 citations)
```

**Generated files (3 files):**
```
/tmp/paper_test/
├── Asai_2023_Self-RAG_*.pdf   # Downloaded PDF (1.4 MB)
├── citation.bib                # BibTeX citation
└── references.txt              # 50 citation references
```

### Paper Command Options

| Option | Default | Description |
|--------|---------|-------------|
| `-o, --output` | `./output` | Output directory |
| `--bibtex/--no-bibtex` | `True` | Generate BibTeX citation file |
| `--references/--no-references` | `True` | Fetch and save citation references |
| `--markdown` | `False` | Extract PDF to markdown (optional) |
| `--max-refs` | `50` | Maximum references to fetch |

---

## Step 4: Ingest PDF to Markdown

Convert the downloaded PDF to markdown with extracted images.

```bash
uv run ingestor ingest "/tmp/paper_test/Asai_2023_Self-RAG_Learning_to_Retrieve_Generate_and_Critiqu.pdf" -o /tmp/paper_test/ingested
```

**Output:**
```
Success! Output written to: /tmp/paper_test/ingested/Asai_2023_Self-RAG_*_pdf
  Images: 3
```

**Generated files:**
```
/tmp/paper_test/ingested/Asai_2023_Self-RAG_*_pdf/
├── Asai_2023_Self-RAG_*_pdf.md    # Full markdown with image refs
└── img/
    ├── *_img_001.png
    ├── *_img_002.png
    └── *_img_003.png
```

---

## Commands Reference

| Command | Purpose | Output |
|---------|---------|--------|
| `ingestor research "query" -o DIR` | Deep research with Gemini | `research_report.md`, `research_metadata.json` |
| `ingestor parse-refs FILE` | Extract references | `references.json`, `references.md` |
| `ingestor paper "arXiv:ID" -o DIR` | Download paper | `*.pdf`, `citation.bib`, `references.txt` |
| `ingestor ingest FILE.pdf -o DIR` | PDF to markdown | `*.md`, `img/*.png` |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Gemini API key for deep research |
| `INGESTOR_EMAIL` | Email for CrossRef/Unpaywall API access |
| `S2_API_KEY` | Semantic Scholar API key (optional) |

---

## Example: Full Pipeline

```bash
# Set API key
export GOOGLE_API_KEY=<your-gemini-api-key>

# Step 1: Research
uv run ingestor research "What are the best techniques for RAG systems?" -o ./rag_research

# Step 2: Parse references
uv run ingestor parse-refs ./rag_research/research/research_report.md

# Step 3: Download papers (from references.json)
uv run ingestor paper "arXiv:2005.11401" -o ./rag_research/papers  # Original RAG
uv run ingestor paper "arXiv:2404.16130" -o ./rag_research/papers  # GraphRAG
uv run ingestor paper "arXiv:2310.11511" -o ./rag_research/papers  # Self-RAG

# Step 4: Ingest PDFs to markdown
uv run ingestor ingest "./rag_research/papers/*.pdf" -o ./rag_research/ingested
```

**Final output structure:**
```
./rag_research/
├── research/
│   ├── research_report.md
│   ├── research_metadata.json
│   ├── references.md
│   └── references.json
├── papers/
│   ├── Lewis_2020_*.pdf
│   ├── Edge_2024_*.pdf
│   ├── Asai_2023_*.pdf
│   ├── citation.bib
│   └── references.txt
└── ingested/
    ├── Lewis_2020_*_pdf/
    │   ├── *.md
    │   └── img/
    ├── Edge_2024_*_pdf/
    │   ├── *.md
    │   └── img/
    └── Asai_2023_*_pdf/
        ├── *.md
        └── img/
```
