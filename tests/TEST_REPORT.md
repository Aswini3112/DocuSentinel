# DocuSentinel AI — Test Report

## Test Suite Coverage

| Module | Test File | Tests | Coverage Areas |
|--------|-----------|-------|----------------|
| Document Extraction | `test_extraction.py` | 11 | PDF/DOCX/TXT/Image extraction, empty files, unicode, large files |
| Chunking Engine | `test_chunker.py` | 9 | Overlap, metadata, sequential index, multi-page, raw text |
| Claim Extractor | `test_claim_extractor.py` | 10 | Deadlines, amounts, duration, deduplication, normalization |
| Conflict Engine | `test_conflict_engine.py` | 13 | Deadline/payment conflicts, single doc no-conflict, severity, summary |
| Uncertainty Engine | `test_uncertainty_engine.py` | 10 | Confidence scoring, status classification, conflict penalty |
| API Endpoints | `test_api.py` | 18 | All routes: health, upload, list, investigate, conflicts, evidence |

**Total: 71 tests**

---

## How to Run Tests

```bash
cd "d:\DocuSentinel AI"
pip install -r backend/requirements.txt
pytest
```

Run a specific test file:
```bash
pytest tests/test_conflict_engine.py -v
```

Run with coverage report:
```bash
pip install pytest-cov
pytest --cov=backend --cov-report=term-missing
```

---

## Key Test Cases for Judging

### Edge Cases Covered

| Scenario | Test | Expected |
|----------|------|----------|
| Empty document upload | `test_upload_empty_file` | 400 Bad Request |
| Unsupported file type | `test_upload_unsupported_type` | 415 Unsupported |
| Question with no documents | `test_investigate_no_documents` | NOT_FOUND status, 0% confidence |
| Conflicting deadlines | `test_deadline_conflict_detected` | InlineConflict detected |
| Consistent evidence | `test_consistent_evidence_no_conflict` | No conflict generated |
| Single-doc evidence | `test_no_conflict_single_document` | No cross-doc conflict |
| Multiple HIGH conflicts | `test_high_conflict_makes_uncertain` | Confidence < 50% |
| Uncertainty phrases in answer | `test_uncertainty_phrases_trigger_uncertain` | UNCERTAIN status |
| Invalid API filters | `test_list_conflicts_invalid_severity` | 400 Bad Request |
| Non-existent resources | Multiple 404 tests | 404 responses |

---

## Notes

- Tests use an **in-memory SQLite database** (no real file system side effects)
- OpenAI API is **not called** during tests (mocked or fallback mode)
- ChromaDB is **not initialized** during API tests (vector store mocked)
- All tests are designed to run offline without external services
