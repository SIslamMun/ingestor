# Pipeline Report

**Topic:** Retrieval Augmented Generation
**Generated:** 2025-12-29 08:43:57

## Pipeline Steps

| Step | Description | Output |
|------|-------------|--------|
| 1. Research | Deep research on topic | `1_research/` |
| 2. Parse Refs | Extract DOIs, arXiv, GitHub, URLs | `2_references/` |
| 3. Retrieve | Download papers + BibTeX | `3_papers/`, `3_bibtex/` |
| 4. Ingest | Convert to markdown | `4_markdown/` |

## Extracted References

- **DOIs:** 0
- **arXiv papers:** 10
- **GitHub repos:** 10
- **URLs:** 53

## Retrieved

- **Papers downloaded:** 3
- **BibTeX entries:** 3

## Ingested

- **PDFs converted:** 2
- **GitHub repos:** 2
- **URLs:** 3

## Output Structure

```
pipeline_output_cli/
├── 1_research/          # Deep research output
│   └── research_report.md
├── 2_references/        # Extracted references
│   ├── references.json
│   └── references.md
├── 3_papers/            # Downloaded PDFs
├── 3_bibtex/            # BibTeX citations
│   └── combined.bib
└── 4_markdown/          # Final markdown for RAG
    ├── papers/
    ├── github/
    ├── web/
    └── research/
```

## Usage

All markdown files in `4_markdown/` are ready for RAG ingestion.
