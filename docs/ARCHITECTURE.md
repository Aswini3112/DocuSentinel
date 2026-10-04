# DocuSentinel AI — Architecture Document

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                           │
│                    http://localhost:5173                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP (Vite /api proxy)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    REACT / VITE FRONTEND                        │
│                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐ ┌───────────────┐  │
│  │Dashboard │ │Documents │ │ Investigate  │ │   Conflicts   │  │
│  └──────────┘ └──────────┘ └─────────────┘ └───────────────┘  │
│  ┌──────────────────────┐  ┌─────────────────────────────────┐ │
│  │  Evidence + Graph    │  │   Settings / System Status      │ │
│  └──────────────────────┘  └─────────────────────────────────┘ │
│                                                                 │
│  State: TanStack React Query · Zustand                          │
│  Graph: React Flow (document-claim-conflict nodes/edges)        │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST API
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND  :8000                       │
│                                                                 │
│  POST /api/documents/upload    GET  /api/documents              │
│  POST /api/investigate         GET  /api/investigations         │
│  GET  /api/conflicts           PATCH /api/conflicts/{id}        │
│  GET  /api/evidence/graph/data GET  /api/health                 │
│  GET  /api/stats                                                │
└──────┬──────────────────────────────────────────┬──────────────┘
       │                                          │
       ▼                                          ▼
┌──────────────────────┐              ┌───────────────────────────┐
│  DOCUMENT INGESTION  │              │   INVESTIGATION PIPELINE  │
│  (Background Task)   │              │                           │
│                      │              │ 1. embed_query()           │
│ 1. save to disk      │              │ 2. vector_store.query()   │
│ 2. extract_document()│              │ 3. deduplicate_evidence() │
│    PDF → PyMuPDF     │              │ 4. detect_inline_        │
│    DOCX → python-docx│              │    conflicts()            │
│    TXT  → plain read │              │ 5. generate_answer()      │
│    IMG  → tesseract  │              │    (LLM or fallback)      │
│ 3. chunk_pages()     │              │ 6. compute_confidence()   │
│    (sliding window)  │              │ 7. classify_answer_state()│
│ 4. embed_texts()     │              │ 8. persist Investigation  │
│    OpenAI or local   │              │                           │
│ 5. vector_store      │              └───────────────────────────┘
│    .add_embeddings() │
│ 6. extract_claims()  │
│    (regex patterns)  │
│ 7. detect_conflicts_ │
│    for_document()    │
└──────────────────────┘
       │                              │
       ▼                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                               │
│                                                                 │
│  ┌─────────────────────────┐   ┌──────────────────────────────┐ │
│  │   SQLite (async)        │   │   ChromaDB (persistent)      │ │
│  │                         │   │                              │ │
│  │  documents              │   │  Collection: docusentinel_   │ │
│  │  document_chunks        │   │  chunks                      │ │
│  │  claims                 │   │                              │ │
│  │  conflicts              │   │  Each vector stores:         │ │
│  │  investigations         │   │  - embedding (float[])       │ │
│  │                         │   │  - text                      │ │
│  │  Managed by SQLAlchemy  │   │  - metadata:                 │ │
│  │  async ORM              │   │    chunk_id, document_id,    │ │
│  │                         │   │    document_name, page,      │ │
│  └─────────────────────────┘   │    section, chunk_index      │ │
│                                └──────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                            │
│                                                                 │
│  ┌────────────────────────┐   ┌──────────────────────────────┐  │
│  │  OpenAI API (optional) │   │  Local Fallback (no key)     │  │
│  │                        │   │                              │  │
│  │  text-embedding-3-small│   │  sentence-transformers       │  │
│  │  gpt-4o-mini           │   │  all-MiniLM-L6-v2 (384-dim) │  │
│  │                        │   │  deterministic answer builder│  │
│  └────────────────────────┘   └──────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Conflict Detection Architecture

Two complementary engines run at different times:

```
INGESTION TIME (background, per document)
─────────────────────────────────────────
New document ingested
        │
        ▼
extract_claims_from_chunks()
   regex patterns for:
   deadline / start_date / payment_amount /
   project_owner / penalty / duration / version
        │
        ▼
For each claim → compare against all claims
from OTHER documents with same field
        │
        ▼
_values_conflict()
   ├── exact match?     → no conflict
   ├── numeric field?   → check > 1% difference
   └── text field?      → normalized comparison
        │
        ▼
Conflict record saved to DB (field, doc_a, doc_b, value_a, value_b, severity)

QUERY TIME (inline, per investigation)
──────────────────────────────────────
Evidence chunks retrieved for question
        │
        ▼
detect_inline_conflicts(evidence)
   ├── group evidence by document
   ├── extract facts per document (regex)
   └── compare same-field facts across docs
        │
        ▼
InlineConflict list returned
   ├── Included in InvestigateResponse
   ├── Shown in UI Conflicts tab
   └── Used to reduce confidence score
```

---

## Confidence Scoring Formula

```
Score (0–100) = retrieval_relevance + source_count + source_agreement + completeness

retrieval_relevance:
  avg(top-3 relevance scores) × 40
  → max 40 pts

source_count:
  unique_docs × 10, capped at 20
  → max 20 pts

source_agreement:
  25 pts base
  − (high_severity_conflicts × 15)
  − (medium_severity_conflicts × 8)
  → min 0 pts

completeness:
  chunk_count × 3, capped at 15
  → max 15 pts

Total: max 100 pts

Answer Status:
  score ≥ 70 AND no conflicts → VERIFIED
  any conflicts               → CONFLICTING
  score ≥ 35 AND < 70         → UNCERTAIN
  no evidence                 → NOT_FOUND
```

---

## API Contract Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/documents/upload` | Upload + ingest document |
| GET | `/api/documents` | List all documents |
| GET | `/api/documents/{id}` | Document detail + sample chunks |
| DELETE | `/api/documents/{id}` | Remove document |
| POST | `/api/documents/demo/load` | Load synthetic demo documents |
| POST | `/api/investigate` | Run document investigation |
| GET | `/api/investigations` | List past investigations |
| GET | `/api/investigations/{id}` | Get investigation detail |
| GET | `/api/conflicts` | List all conflicts (filter by severity/status) |
| GET | `/api/conflicts/{id}` | Get conflict detail |
| PATCH | `/api/conflicts/{id}` | Update conflict status |
| GET | `/api/evidence/{chunk_id}` | Get evidence chunk |
| GET | `/api/evidence/document/{id}` | Paginated chunks for a document |
| GET | `/api/evidence/graph/data` | Graph nodes + edges for React Flow |
| GET | `/api/health` | System health check |
| GET | `/api/stats` | Dashboard statistics |

---

## Database Schema

```
documents
  id, original_name, stored_name, file_type, file_size,
  file_hash, status, page_count, chunk_count, error_message,
  is_demo, created_at, updated_at

document_chunks
  id, document_id (FK), chunk_index, text,
  page_number, section, char_start, char_end, created_at

claims
  id, document_id (FK), chunk_id (FK), field,
  raw_value, normalized_value, page_number,
  context_text, created_at

conflicts
  id, field, claim_a_id (FK), claim_b_id (FK),
  document_a_id (FK), document_b_id (FK),
  value_a, value_b, severity, status,
  description, created_at

investigations
  id, question, answer, answer_status,
  confidence_score, confidence_reason,
  evidence_strength, has_conflict,
  evidence_json, sources_json, conflicts_json,
  created_at
```

---

## File Structure

```
DocuSentinel AI/
├── README.md
├── .env.example
├── .gitignore
├── pytest.ini
├── start_backend.ps1 / .sh
├── start_frontend.ps1 / .sh
│
├── backend/
│   ├── main.py              # FastAPI app + lifespan
│   ├── config.py            # Pydantic settings
│   ├── database.py          # Async SQLAlchemy engine
│   ├── .env                 # Local environment (gitignored)
│   ├── requirements.txt
│   ├── models/
│   │   ├── db_models.py     # SQLAlchemy ORM models
│   │   └── schemas.py       # Pydantic request/response schemas
│   ├── routes/
│   │   ├── health.py
│   │   ├── documents.py
│   │   ├── investigate.py
│   │   ├── conflicts.py
│   │   └── evidence.py
│   ├── services/
│   │   ├── extractor.py     # PDF/DOCX/TXT/Image extraction
│   │   ├── chunker.py       # Sliding window chunker
│   │   ├── embedder.py      # OpenAI + local fallback
│   │   ├── vector_store.py  # ChromaDB wrapper
│   │   ├── retrieval.py     # Semantic search
│   │   ├── claim_extractor.py # Regex claim extraction
│   │   ├── ingestion.py     # Pipeline orchestrator
│   │   ├── conflict_engine.py # Conflict detection
│   │   ├── rag_engine.py    # Grounded answer generation
│   │   ├── uncertainty_engine.py # Confidence scoring
│   │   └── investigator.py  # Investigation orchestrator
│   └── utils/
│       ├── file_utils.py    # Validation, hashing, naming
│       └── text_utils.py    # Cleaning, normalization, regex
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── .env.example
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/client.ts    # Typed Axios API client
│       ├── styles/globals.css
│       ├── components/
│       │   ├── Layout.tsx
│       │   ├── StatusBadge.tsx
│       │   ├── ConfidenceBar.tsx
│       │   ├── LoadingSpinner.tsx
│       │   ├── EmptyState.tsx
│       │   └── EvidenceGraph.tsx  # React Flow graph
│       └── pages/
│           ├── DashboardPage.tsx
│           ├── DocumentsPage.tsx
│           ├── InvestigatePage.tsx
│           ├── ConflictsPage.tsx
│           ├── EvidencePage.tsx
│           └── SettingsPage.tsx
│
├── data/
│   ├── demo/                # 5 synthetic conflict-rich documents
│   ├── uploads/             # Uploaded files (gitignored)
│   └── vectorstore/         # ChromaDB data (gitignored)
│
├── tests/
│   ├── conftest.py
│   ├── test_extraction.py   (11 tests)
│   ├── test_chunker.py      (9 tests)
│   ├── test_claim_extractor.py (10 tests)
│   ├── test_conflict_engine.py (13 tests)
│   ├── test_uncertainty_engine.py (10 tests)
│   ├── test_api.py          (18 tests)
│   └── TEST_REPORT.md
│
└── docs/
    └── ARCHITECTURE.md      # This file
```
