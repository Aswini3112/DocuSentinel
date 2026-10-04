# DocuSentinel AI

> **"Investigate documents. Trace evidence. Detect conflicts. Trust the answer."**

Built for **ALGOTHON'26** · Problem Statement **ALG-AI-02: Intelligent Document Investigator**

---

## What Is DocuSentinel AI?

Most document AI systems focus on **answering**.  
DocuSentinel focuses on **whether the answer can be trusted**.

DocuSentinel AI is a professional document investigation platform that:

- Accepts multiple documents (PDF, DOCX, TXT, Images)
- Extracts, chunks, and indexes all content with full source metadata
- Answers natural-language questions grounded strictly in retrieved evidence
- **Detects contradictions** between documents and surfaces them explicitly
- **Refuses to hallucinate** — communicates uncertainty instead of inventing facts
- Provides a transparent confidence score with explainable reasoning
- Classifies every answer: `VERIFIED` · `CONFLICTING` · `UNCERTAIN` · `NOT_FOUND`

---

## Problem Statement

> Information is scattered across PDFs, images and text documents.  
> Users need answers without manually reading every document.

**ALG-AI-02 Mandatory Requirements:**

| Requirement | DocuSentinel Implementation |
|---|---|
| Multiple document formats | PDF, DOCX, TXT, PNG/JPG/TIFF (OCR) |
| Extraction / indexing | PyMuPDF + python-docx + pytesseract + ChromaDB |
| Natural-language Q&A | RAG with OpenAI GPT-4o-mini (local fallback) |
| Source / section references | Every answer cites document + page + section |
| Conflict detection | Dual-engine: post-ingestion DB claims + query-time inline |
| Uncertainty handling | 4-state system: VERIFIED / CONFLICTING / UNCERTAIN / NOT_FOUND |

---

## Key Features

### Evidence-First AI
The LLM is instructed by a strict system prompt: *"You may only make claims supported by retrieved evidence."* If evidence is absent or insufficient, the system says so.

### Dual Conflict Detection
1. **Post-ingestion**: After each document is indexed, its extracted claims (dates, amounts, names) are compared against all existing claims from other documents. Conflicts are stored in the database.
2. **Query-time inline**: When answering a question, retrieved evidence chunks are scanned for contradictory facts across different source documents in real time.

### Transparent Confidence Scoring
Every answer comes with an explainable confidence score calculated from four factors:
- Retrieval relevance (semantic similarity)
- Number of unique supporting sources
- Source agreement (penalized for conflicts)
- Evidence completeness (chunk count)

### Document Relation Graph
An interactive React Flow graph visualizes which documents support which claims and which claims contradict each other.

---

## Architecture

```
User
 │
 ▼
React/Vite Frontend (port 5173)
 │  ├── Dashboard      — stats, health, recent activity
 │  ├── Documents      — drag-drop upload, processing status
 │  ├── Investigate    — Q&A workspace with tabbed evidence
 │  ├── Conflicts      — conflict dashboard with comparison
 │  ├── Evidence       — chunk browser + relation graph
 │  └── Settings       — system status, config reference
 │
 ▼ (HTTP /api proxy → port 8000)
FastAPI Backend
 │
 ├── POST /api/documents/upload
 │    └── Background: Extraction → Chunking → Embedding → ChromaDB → Claim Extraction → Conflict Detection
 │
 ├── POST /api/investigate
 │    └── Embed query → Vector search → Inline conflict detect → LLM answer → Confidence score
 │
 ├── GET  /api/conflicts
 │    └── DB-stored claim-level conflicts with severity
 │
 ├── GET  /api/evidence/graph/data
 │    └── Documents + claims + conflict edges for React Flow
 │
 └── GET  /api/health  |  GET /api/stats
      └── Subsystem status + dashboard metrics

Services Layer
 ├── extractor.py      — PDF (PyMuPDF), DOCX, TXT, Image (pytesseract)
 ├── chunker.py        — sliding window with overlap, preserves page/section
 ├── embedder.py       — OpenAI text-embedding-3-small (local fallback: all-MiniLM-L6-v2)
 ├── vector_store.py   — ChromaDB persistent store
 ├── retrieval.py      — semantic search + deduplication
 ├── claim_extractor.py— regex claim extraction (dates, amounts, names)
 ├── conflict_engine.py— DB comparison + inline evidence conflict detection
 ├── rag_engine.py     — grounded answer generation (anti-hallucination)
 ├── uncertainty_engine.py — 4-factor confidence scoring
 └── investigator.py   — orchestrator tying all services

Data Layer
 ├── SQLite (async)    — documents, chunks, claims, conflicts, investigations
 └── ChromaDB          — persistent vector store (cosine similarity)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite 5, Tailwind CSS 3 |
| State / Data | Zustand, TanStack React Query |
| Graph | React Flow 11 |
| Backend | FastAPI, Python 3.11+, Uvicorn |
| ORM | SQLAlchemy 2 (async), aiosqlite |
| Vector DB | ChromaDB (persistent) |
| Embeddings | OpenAI text-embedding-3-small / sentence-transformers (fallback) |
| LLM | OpenAI GPT-4o-mini / deterministic fallback |
| PDF | PyMuPDF (fitz) |
| DOCX | python-docx |
| OCR | pytesseract + Pillow |
| Testing | pytest, pytest-asyncio, httpx |

---

## Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm 9+
- (Optional) Tesseract OCR for image documents
- (Optional) OpenAI API key

### Quick Start (Windows)

```powershell
# Terminal 1 — Backend
cd "d:\DocuSentinel AI"
.\start_backend.ps1

# Terminal 2 — Frontend
cd "d:\DocuSentinel AI"
.\start_frontend.ps1
```

### Quick Start (Linux / macOS)

```bash
# Terminal 1 — Backend
bash start_backend.sh

# Terminal 2 — Frontend
bash start_frontend.sh
```

### Manual Setup

```bash
# Backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt

cd backend
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## Environment Variables

Copy `.env.example` to `backend/.env` and configure:

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Recommended | — | GPT-4o-mini + embeddings. System works without it using local models. |
| `LLM_MODEL` | No | `gpt-4o-mini` | OpenAI model for answer generation |
| `EMBEDDING_MODEL` | No | `text-embedding-3-small` | OpenAI embedding model |
| `CHUNK_SIZE` | No | `500` | Words per document chunk |
| `CHUNK_OVERLAP` | No | `50` | Overlapping words between chunks |
| `TOP_K_RETRIEVAL` | No | `6` | Evidence chunks to retrieve per query |
| `MAX_FILE_SIZE_MB` | No | `50` | Max upload size |
| `DEBUG` | No | `false` | Enable SQLAlchemy query logging |

> **Without OpenAI key:** The system automatically falls back to `sentence-transformers/all-MiniLM-L6-v2` (local, free) for embeddings, and constructs deterministic evidence-based answers without calling the LLM.

---

## How to Run

1. Start the backend (`uvicorn` on port 8000)
2. Start the frontend (`vite` on port 5173)
3. Open `http://localhost:5173`
4. Click **"Load Demo Data"** on the Documents page
5. Wait for all 5 demo documents to reach **Ready** status
6. Navigate to **Investigate** and ask: *"What is the project deadline?"*

---

## How to Test

```bash
cd "d:\DocuSentinel AI"

# Activate virtual environment first
venv\Scripts\activate     # Windows
source venv/bin/activate  # Linux/macOS

# Run all 71 tests
pytest

# Run specific suite
pytest tests/test_conflict_engine.py -v
pytest tests/test_uncertainty_engine.py -v
pytest tests/test_api.py -v

# With coverage
pip install pytest-cov
pytest --cov=backend --cov-report=term-missing
```

---

## Demo Workflow (3 minutes)

| Step | Action | What to Show |
|---|---|---|
| 1 | Open DocuSentinel dashboard | Stats cards, health indicator |
| 2 | Documents → Load Demo Data | 5 files queuing and processing |
| 3 | Wait for all documents → Ready | Page count, chunk count per doc |
| 4 | Investigate → *"What is the project deadline?"* | Answer + evidence + sources |
| 5 | Investigate → *"Do all documents agree on the deadline?"* | **⚠ CONFLICT DETECTED** banner |
| 6 | Click Conflicts tab | Side-by-side: 15 Nov vs 30 Nov |
| 7 | Conflicts dashboard | High/Medium/Low severity cards |
| 8 | Investigate → *"What is the total contract value?"* | THREE conflicting values |
| 9 | Evidence → Relation Graph | Animated conflict edges |
| 10 | Investigate → *"What is the penalty for nuclear incidents?"* | **NOT_FOUND** — system refuses to hallucinate |

**Key message for judges:** *"DocuSentinel refuses to give you a confident wrong answer. It tells you when it doesn't know, and it tells you when the documents disagree with each other."*

---

## Demo Conflicts Reference

All demo documents are **synthetic** and contain intentional contradictions:

| Conflict | Doc A | Doc B | Severity |
|---|---|---|---|
| Project deadline | 15 Nov 2026 | 30 Nov 2026 | HIGH |
| Contract value | USD 1,200,000 | USD 1,450,000 (+ USD 1,380,000) | HIGH |
| Penalty cap | USD 120,000 | USD 75,000 | HIGH |
| Late payment rate | 2% / month | 1.5% / month | MEDIUM |
| Project manager | Arjun Mehta | Vikram Sharma | MEDIUM |

---

## Innovation

1. **Dual-engine conflict detection** — both structural (claim DB) and semantic (evidence-level inline)
2. **Anti-hallucination by design** — strict LLM system prompt + local fallback that never invents facts
3. **4-state answer classification** — not just "here's an answer" but *what kind* of answer
4. **Explainable confidence** — score broken into four named factors, not a black box
5. **Evidence-first UI** — every answer tab shows Evidence → Sources → Conflicts, not just text
6. **Document Relation Graph** — visual proof of contradictions across documents

---

## Limitations

- OCR quality depends on Tesseract installation and image quality
- Conflict detection is regex-based for structured fields; unstructured contradictions rely on LLM
- Confidence score is heuristic, not statistically calibrated
- Vector search quality depends on embedding model (OpenAI > local fallback)
- Large PDFs (>200 pages) may take 30–60 seconds to ingest

---

## Future Improvements

- Multi-language document support
- Table and figure extraction from PDFs
- User authentication and document access control
- Persistent investigation workspaces / sessions
- Fine-tuned claim extraction model
- Batch document comparison reports
- Export investigation results to PDF

---

## AI / API Disclosure

| Component | Technology |
|---|---|
| Answer generation | OpenAI GPT-4o-mini (configurable) |
| Embeddings | OpenAI text-embedding-3-small OR sentence-transformers/all-MiniLM-L6-v2 |
| OCR | Tesseract (local, open source) |
| Vector search | ChromaDB cosine similarity (local) |
| All other logic | Custom Python — no AI APIs |

The system is fully functional without an OpenAI API key using the local fallback.

---

*DocuSentinel AI — ALGOTHON'26 · ALG-AI-02*
