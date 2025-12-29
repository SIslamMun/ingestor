# Pipeline Report

**Topic:** Lightweight Fine-Tuned LLMs with Reasoning Capabilities
**Generated:** 2025-12-29 09:42:53

## Configuration

### Phase 1: Research
| Setting | Value |
|---------|-------|
| Skip | True |
| Verbose | False |
| Stream | True |

### Phase 2: Parse References
| Setting | Value |
|---------|-------|
| Format | both |

### Phase 3: Paper Retrieval
| Setting | Value |
|---------|-------|
| Max Papers | 1 |
| Skip Existing | True |
| Verify BibTeX | True |
| BibTeX Format | bibtex |

### Phase 4: Ingestion
| Setting | Value |
|---------|-------|
| Git Mode | readme |
| Shallow Clone | True |
| Branch | default |
| Max Files/Repo | unlimited |
| Max Repos | None |
| Max URLs | 1 |
| Max YouTube | 1 |
| Deep Crawl | True |
| Crawl Depth | 2 |
| Crawl Pages | 1 |
| VLM Describe | True |
| Claude Agent | True |

## Pipeline Steps

| Step | Description | Output |
|------|-------------|--------|
| 1. Research | Deep research on topic | `1_research/` |
| 2. Parse Refs | Extract DOIs, arXiv, GitHub, YouTube, URLs | `2_references/` |
| 3. Retrieve | Download papers + BibTeX | `3_papers/`, `3_bibtex/` |
| 4. Ingest | Convert to markdown | `4_markdown/` |

## Extracted References

- **DOIs:** 0
- **arXiv papers:** 6
- **GitHub repos:** 5
- **YouTube videos:** 5
- **URLs:** 81

## Retrieved

- **Papers downloaded:** 1
- **BibTeX entries:** 1

## Ingested

- **PDFs converted:** 1
- **GitHub repos:** 5
- **YouTube videos:** 1
- **URLs:** 1

## Output Structure

```
int_test/
├── 1_research/          # Deep research output
│   └── research_report.md
├── 2_references/        # Extracted references
│   ├── references.json
│   └── references.md
├── 3_papers/            # Downloaded PDFs
├── 3_bibtex/            # BibTeX citations
│   ├── combined.bib
│   └── verified/
└── 4_markdown/          # Final markdown for RAG
    ├── papers/
    ├── github/
    ├── youtube/
    ├── web/
    └── research/
```

## Usage

All markdown files in `4_markdown/` are ready for RAG ingestion.
