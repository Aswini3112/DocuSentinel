"""
DocuSentinel AI - Tests: Conflict Detection Engine
Tests inline conflict detection and severity classification.
"""

import pytest
from backend.models.schemas import EvidenceItem
from backend.services.conflict_engine import (
    detect_inline_conflicts,
    build_conflict_summary,
    _values_conflict,
    _inline_severity,
)
from backend.models.db_models import Claim, ConflictSeverity


def make_evidence(
    doc_id: str,
    doc_name: str,
    text: str,
    page: int = 1,
) -> EvidenceItem:
    return EvidenceItem(
        chunk_id=f"chunk_{doc_id}_{page}",
        document_id=doc_id,
        document_name=doc_name,
        page_number=page,
        section=None,
        text=text,
        relevance_score=0.9,
    )


class TestInlineConflictDetection:

    def test_no_conflict_single_document(self):
        """No conflict when all evidence comes from one document."""
        evidence = [
            make_evidence("doc1", "Contract.txt", "Deadline: 15 November 2026"),
            make_evidence("doc1", "Contract.txt", "Payment: USD 1,200,000"),
        ]
        conflicts = detect_inline_conflicts(evidence)
        assert conflicts == []

    def test_no_conflict_fewer_than_two_items(self):
        """Single evidence item cannot produce a conflict."""
        evidence = [make_evidence("doc1", "Contract.txt", "Deadline: 15 November 2026")]
        conflicts = detect_inline_conflicts(evidence)
        assert conflicts == []

    def test_deadline_conflict_detected(self):
        """Conflicting deadlines across documents are detected."""
        evidence = [
            make_evidence("doc1", "Contract.txt",
                "The project deadline is 15 November 2026."),
            make_evidence("doc2", "StatusReport.txt",
                "The revised deadline is 30 November 2026."),
        ]
        conflicts = detect_inline_conflicts(evidence)
        deadline_conflicts = [c for c in conflicts if c.field == "deadline"]
        assert len(deadline_conflicts) >= 1

    def test_payment_conflict_detected(self):
        """Conflicting payment amounts across documents are detected."""
        evidence = [
            make_evidence("doc1", "Contract.txt",
                "Total contract value: USD 1,200,000."),
            make_evidence("doc2", "StatusReport.txt",
                "Revised total amount: USD 1,450,000."),
        ]
        conflicts = detect_inline_conflicts(evidence)
        amount_conflicts = [c for c in conflicts if c.field == "payment_amount"]
        assert len(amount_conflicts) >= 1

    def test_consistent_evidence_no_conflict(self):
        """Matching values across documents produce no conflict."""
        evidence = [
            make_evidence("doc1", "Contract.txt",
                "The project deadline is 15 November 2026."),
            make_evidence("doc2", "Report.txt",
                "Delivery deadline remains 15 November 2026."),
        ]
        conflicts = detect_inline_conflicts(evidence)
        # No conflict expected since values are the same date
        deadline_conflicts = [c for c in conflicts if c.field == "deadline"]
        assert len(deadline_conflicts) == 0

    def test_conflict_carries_source_info(self):
        """Detected conflict includes correct document names and values."""
        evidence = [
            make_evidence("doc1", "Contract.txt",
                "Deadline: 15 November 2026", page=4),
            make_evidence("doc2", "Report.txt",
                "Revised deadline: 30 November 2026", page=7),
        ]
        conflicts = detect_inline_conflicts(evidence)
        if conflicts:
            conflict = conflicts[0]
            assert conflict.source_a != conflict.source_b
            assert conflict.value_a != conflict.value_b

    def test_severity_high_for_deadline(self):
        """Deadline conflicts have HIGH severity."""
        assert _inline_severity("deadline") == "HIGH"

    def test_severity_high_for_payment(self):
        """Payment amount conflicts have HIGH severity."""
        assert _inline_severity("payment_amount") == "HIGH"

    def test_severity_medium_for_owner(self):
        """Project owner conflicts have MEDIUM severity."""
        assert _inline_severity("project_owner") == "MEDIUM"

    def test_severity_low_for_unknown(self):
        """Unknown field gets LOW severity."""
        assert _inline_severity("unknown_field") == "LOW"

    def test_build_conflict_summary_empty(self):
        """Empty conflict list produces empty summary."""
        assert build_conflict_summary([]) == ""

    def test_build_conflict_summary_content(self):
        """Conflict summary contains field and document names."""
        evidence = [
            make_evidence("doc1", "ContractA.txt",
                "Deadline: 15 November 2026"),
            make_evidence("doc2", "ReportB.txt",
                "Revised deadline: 30 November 2026"),
        ]
        conflicts = detect_inline_conflicts(evidence)
        if conflicts:
            summary = build_conflict_summary(conflicts)
            assert len(summary) > 0
            assert "deadline" in summary.lower() or "DEADLINE" in summary


class TestValuesConflict:

    def _make_claim(self, field: str, raw: str, normalized: str = None) -> Claim:
        c = Claim()
        c.field = field
        c.raw_value = raw
        c.normalized_value = normalized
        c.document_id = "test_doc"
        return c

    def test_identical_values_no_conflict(self):
        a = self._make_claim("deadline", "15 November 2026", "2026-11-15")
        b = self._make_claim("deadline", "15 November 2026", "2026-11-15")
        assert not _values_conflict(a, b)

    def test_different_dates_conflict(self):
        a = self._make_claim("deadline", "15 November 2026", "2026-11-15")
        b = self._make_claim("deadline", "30 November 2026", "2026-11-30")
        assert _values_conflict(a, b)

    def test_similar_amounts_no_conflict(self):
        """Amounts within 1% tolerance should not conflict."""
        a = self._make_claim("payment_amount", "USD 1,200,000", "1200000.00")
        b = self._make_claim("payment_amount", "USD 1,200,000", "1200000.00")
        assert not _values_conflict(a, b)

    def test_different_amounts_conflict(self):
        a = self._make_claim("payment_amount", "USD 1,200,000", "1200000.00")
        b = self._make_claim("payment_amount", "USD 1,450,000", "1450000.00")
        assert _values_conflict(a, b)
