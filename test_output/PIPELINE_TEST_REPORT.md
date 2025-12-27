# Research-to-Ingest Pipeline Test Report

**Date:** December 27, 2025  
**Repository:** ingestor  
**Branch:** master

---

## 📋 Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RESEARCH-TO-INGEST PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │   parser     │───▶│   parser     │───▶│   parser     │───▶│  parser   │ │
│  │   refs       │    │   retrieve   │    │   doi2bib    │    │  verify   │ │
│  │              │    │              │    │              │    │           │ │
│  │ Extract refs │    │ Download     │    │ Generate     │    │ Validate  │ │
│  │ from .md     │    │ PDFs         │    │ BibTeX       │    │ Citations │ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └───────────┘ │
│         │                   │                   │                   │       │
│         ▼                   ▼                   ▼                   ▼       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         INGESTOR                                      │  │
│  ├──────────────┬──────────────┬──────────────┬──────────────────────────┤  │
│  │   ingestor   │   ingestor   │   ingestor   │      ingestor           │  │
│  │   ingest     │   ingest     │   ingest     │      ingest             │  │
│  │   (PDF)      │   (YouTube)  │   (GitHub)   │      (Web)              │  │
│  └──────────────┴──────────────┴──────────────┴──────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔬 Step 1: Extract References

**Command:**
```bash
parser refs ./research_report.md -o ./test_output/parser/refs
```

**Input:** `research_report.md` (markdown document with citations)

**Output:**
| File | Description |
|------|-------------|
| `references.json` | Structured JSON with categorized refs |
| `references.md` | Human-readable markdown list |

**Results:**
- **31 references extracted**
- GitHub repos: 12
- arXiv papers: 2
- DOI links: 4
- PDF links: 1
- YouTube videos: 3

---

## 📥 Step 2: Retrieve Papers

**Command:**
```bash
parser retrieve -t "Paper Title" -o ./test_output/parser/papers
```

**Sources Used:**
- arXiv (direct + title search)
- Semantic Scholar
- OpenAlex
- PMC (PubMed Central)
- CrossRef
- Unpaywall
- BioRxiv

**Output:**
| File | Paper | Size |
|------|-------|------|
| `10.1038_s41586-020-2649-2.pdf` | NumPy | 1.2 MB |
| `10.1038_s41592-019-0686-2.pdf` | SciPy | 1.6 MB |
| `10.48550_arXiv.1605.08695.pdf` | TensorFlow | 681 KB |
| `10.48550_arXiv.1912.01703.pdf` | PyTorch | 381 KB |
| `pedregosa11a.pdf` | Scikit-learn | 42 KB |

**Total:** 5 PDFs (~3.8 MB)

---

## �� Step 3: Generate BibTeX

**Command:**
```bash
parser doi2bib ./test_output/parser/papers -o ./test_output/parser/bibtex
```

**Output:**
| File | Citation Key |
|------|--------------|
| `numpy.bib` | harris2020array |
| `scipy.bib` | virtanen2019scipy |
| `tensorflow.bib` | abadi2016tensorflow |
| `pytorch.bib` | paszke2019pytorch |
| `combined.bib` | All 4 citations |

---

## ✅ Step 4: Verify Citations

**Command:**
```bash
parser verify ./test_output/parser/bibtex/combined.bib -o ./test_output/parser/verified
```

**Output:**
| File | Description |
|------|-------------|
| `verified.bib` | Validated citations with enriched metadata |
| `failed.bib` | Failed validations (empty) |
| `report.md` | Verification summary |

**Results:**
| Status | Count |
|--------|-------|
| DOI Verified | 1 |
| arXiv Verified | 3 |
| **Total Verified** | **4/4 (100%)** |

---

## 📄 Step 5: Ingest PDFs

**Command:**
```bash
ingestor ingest ./paper.pdf -o ./test_output/ingestor/pdfs
```

**Output:**
| Paper | Lines | Images |
|-------|-------|--------|
| NumPy (Nature) | 257 | 3 |
| SciPy (Nature Methods) | 2,584 | 3 |
| TensorFlow (arXiv) | 583 | 9 |
| PyTorch (NeurIPS) | 291 | 1 |
| Scikit-learn (JMLR) | 184 | 0 |

**Total:** 5 markdown files, 16 images extracted

---

## 🎥 Step 6: Ingest YouTube Videos

**Command:**
```bash
ingestor ingest "https://youtube.com/watch?v=VIDEO_ID" -o ./test_output/ingestor/youtube
```

**Output:**
| Video ID | Title | Duration | Transcript |
|----------|-------|----------|------------|
| J0Aq44Pze-w | Story of Python (Guido) | 4m 1s | ✅ Full |
| DsYIdMmI5-Q | Untold Story of Python | 9m 25s | ✅ Full |
| GnGhI1vKi20 | What is TensorFlow? | 4m 20s | ✅ Full |

**Total:** 3 transcripts with metadata

---

## 🐙 Step 7: Ingest GitHub Repos

**Command:**
```bash
ingestor ingest "https://github.com/owner/repo" -o ./test_output/ingestor/github
```

**Output:**
| Repository | Stars | Language | Lines |
|------------|-------|----------|-------|
| tensorflow | 193,074 | C++ | 59,435 |
| pytorch | 96,158 | Python | 50,545 |
| django | 86,263 | Python | 46,761 |
| flask | 70,972 | Python | 35,703 |
| cpython | 70,479 | Python | 172,294 |
| scikit-learn | 64,387 | Python | 108,812 |
| pandas | 47,422 | Python | 212,968 |
| numpy | 31,094 | Python | 97,389 |
| cython | 10,528 | Python | 155,593 |
| ironpython3 | 2,720 | C# | 141,115 |
| pypy | 1,609 | Python | 131,365 |
| jython | 1,460 | Python | 189,870 |

**Total:** 12 repositories ingested with README + structure

---

## 🌐 Step 8: Ingest Web Pages

**Command:**
```bash
ingestor ingest "https://arxiv.org/abs/1605.08695" -o ./test_output/ingestor/web
```

**Output:**
| URL | Type | Lines |
|-----|------|-------|
| arxiv.org/abs/1605.08695 | arXiv abstract | 124 |
| doi.org/10.1038/s41586-020-2649-2 | DOI landing | 677 |

---

## 📊 Final Summary

### Pipeline Outputs

| Stage | Input | Output | Count |
|-------|-------|--------|-------|
| **refs** | markdown | JSON + MD refs | 31 refs |
| **retrieve** | titles/DOIs | PDFs | 5 papers |
| **doi2bib** | PDFs | BibTeX | 4 citations |
| **verify** | BibTeX | Verified BibTeX | 4/4 verified |
| **ingest PDFs** | PDFs | Markdown + images | 5 docs, 16 imgs |
| **ingest YouTube** | URLs | Transcripts | 3 videos |
| **ingest GitHub** | URLs | Repo content | 12 repos |
| **ingest Web** | URLs | Markdown | 2 pages |

### Test Results

| Category | Passed | Skipped | Failed |
|----------|--------|---------|--------|
| Unit Tests | 755 | 3 | 0 |
| Integration Tests | 94 | 1 | 0 |
| **Total** | **849** | **4** | **0** |

---


