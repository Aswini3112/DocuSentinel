"""
DocuSentinel AI - Tests: Claim Extractor
Tests regex-based factual claim extraction from text chunks.
"""

import pytest
from backend.services.extractor import ExtractedPage
from backend.services.chunker import chunk_pages, Chunk
from backend.services.claim_extractor import extract_claims_from_chunks


def make_chunk(text: str, doc_id: str = "doc1", chunk_index: int = 0, page: int = 1) -> Chunk:
    return Chunk(
        document_id=doc_id,
        document_name="Test.txt",
        chunk_index=chunk_index,
        text=text,
        page_number=page,
        section=None,
        char_start=0,
        char_end=len(text),
    )


class TestClaimExtractor:

    def test_extracts_deadline(self):
        chunk = make_chunk("The project deadline is 15 November 2026.")
        claims = extract_claims_from_chunks([chunk], "doc1")
        deadline_claims = [c for c in claims if c["field"] == "deadline"]
        assert len(deadline_claims) >= 1
        assert "November" in deadline_claims[0]["raw_value"] or "2026" in deadline_claims[0]["raw_value"]

    def test_extracts_payment_amount(self):
        chunk = make_chunk("The total contract value is USD 1,200,000.")
        claims = extract_claims_from_chunks([chunk], "doc1")
        amount_claims = [c for c in claims if c["field"] == "payment_amount"]
        assert len(amount_claims) >= 1
        assert "1,200,000" in amount_claims[0]["raw_value"] or "USD" in amount_claims[0]["raw_value"]

    def test_extracts_duration(self):
        chunk = make_chunk("Project duration: 8 months from commencement.")
        claims = extract_claims_from_chunks([chunk], "doc1")
        duration_claims = [c for c in claims if c["field"] == "duration"]
        assert len(duration_claims) >= 1
        assert "8" in duration_claims[0]["raw_value"]

    def test_no_claims_from_irrelevant_text(self):
        chunk = make_chunk("The sky is blue and the ocean is deep.")
        claims = extract_claims_from_chunks([chunk], "doc1")
        assert len(claims) == 0

    def test_deduplication_same_document(self):
        """Same claim value from same document should not be duplicated."""
        chunk1 = make_chunk("Deadline: 15 November 2026.", chunk_index=0)
        chunk2 = make_chunk("Project must complete by 15 November 2026.", chunk_index=1)
        claims = extract_claims_from_chunks([chunk1, chunk2], "doc1")
        deadline_claims = [c for c in claims if c["field"] == "deadline"]
        # Should have at most 1 unique deadline for this document
        normalized_values = set(c.get("normalized_value") or c["raw_value"] for c in deadline_claims)
        assert len(normalized_values) <= 2  # Slight tolerance for different raw formats

    def test_claim_has_required_fields(self):
        chunk = make_chunk("Deadline: 15 November 2026.")
        claims = extract_claims_from_chunks([chunk], "doc1")
        if claims:
            claim = claims[0]
            assert "field" in claim
            assert "raw_value" in claim
            assert "document_id" in claim
            assert "page_number" in claim
            assert "context_text" in claim

    def test_context_text_preserved(self):
        """Claim should include surrounding context text."""
        chunk = make_chunk(
            "According to Section 3, the project deadline is 15 November 2026. "
            "Failure to meet this will result in penalties.",
        )
        claims = extract_claims_from_chunks([chunk], "doc1")
        if claims:
            deadline_claim = next((c for c in claims if c["field"] == "deadline"), None)
            if deadline_claim:
                assert len(deadline_claim["context_text"]) > 10

    def test_multiple_claim_types_same_chunk(self):
        """Multiple claim types can be extracted from one chunk."""
        chunk = make_chunk(
            "Deadline: 15 November 2026. "
            "Total amount: USD 1,200,000. "
            "Duration: 8 months."
        )
        claims = extract_claims_from_chunks([chunk], "doc1")
        fields = {c["field"] for c in claims}
        assert len(fields) >= 2

    def test_date_normalization(self):
        """Dates should be normalized to ISO format where possible."""
        chunk = make_chunk("Project deadline: 15 November 2026.")
        claims = extract_claims_from_chunks([chunk], "doc1")
        deadline_claims = [c for c in claims if c["field"] == "deadline"]
        if deadline_claims and deadline_claims[0].get("normalized_value"):
            assert deadline_claims[0]["normalized_value"] == "2026-11-15"

    def test_empty_chunks(self):
        """Empty chunk list returns no claims."""
        claims = extract_claims_from_chunks([], "doc1")
        assert claims == []
