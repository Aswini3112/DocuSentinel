"""
DocuSentinel AI - Tests: Uncertainty Engine
Tests confidence scoring and answer state classification.
"""

import pytest
from backend.models.schemas import EvidenceItem, InlineConflict
from backend.models.db_models import AnswerStatus
from backend.services.uncertainty_engine import compute_confidence, classify_answer_state


def make_evidence(doc_id: str, score: float = 0.85) -> EvidenceItem:
    return EvidenceItem(
        chunk_id=f"chunk_{doc_id}",
        document_id=doc_id,
        document_name=f"{doc_id}.txt",
        page_number=1,
        section=None,
        text="Some relevant evidence text about the project deadline.",
        relevance_score=score,
    )


def make_conflict(field: str = "deadline", severity: str = "HIGH") -> InlineConflict:
    return InlineConflict(
        field=field,
        value_a="15 November 2026",
        source_a="Contract.txt",
        page_a=4,
        value_b="30 November 2026",
        source_b="Report.txt",
        page_b=7,
        severity=severity,
    )


class TestComputeConfidence:

    def test_no_evidence_returns_zero(self):
        result = compute_confidence(evidence=[], conflicts=[])
        assert result["score"] == 0.0
        assert result["percent"] == 0
        assert result["status"] == AnswerStatus.NOT_FOUND
        assert result["evidence_strength"] == "None"

    def test_strong_multi_source_evidence(self):
        """Multiple sources with high relevance should yield high confidence."""
        evidence = [make_evidence(f"doc{i}", score=0.90) for i in range(3)]
        result = compute_confidence(evidence=evidence, conflicts=[])

        assert result["score"] > 0.6
        assert result["percent"] > 60
        assert result["status"] in (AnswerStatus.VERIFIED, AnswerStatus.UNCERTAIN)
        assert result["evidence_strength"] in ("High", "Medium")

    def test_conflict_reduces_confidence(self):
        """Conflicts should reduce confidence compared to no-conflict scenario."""
        evidence = [make_evidence(f"doc{i}") for i in range(3)]

        no_conflict = compute_confidence(evidence=evidence, conflicts=[])
        with_conflict = compute_confidence(
            evidence=evidence,
            conflicts=[make_conflict(severity="HIGH")]
        )

        assert with_conflict["percent"] < no_conflict["percent"]
        assert with_conflict["status"] == AnswerStatus.CONFLICTING

    def test_single_weak_evidence(self):
        """Single evidence with low relevance should be low confidence."""
        evidence = [make_evidence("doc1", score=0.25)]
        result = compute_confidence(evidence=evidence, conflicts=[])

        assert result["percent"] < 60
        assert result["evidence_strength"] in ("Low", "Medium")

    def test_reason_contains_bullets(self):
        """Confidence reason should contain bullet points."""
        evidence = [make_evidence("doc1"), make_evidence("doc2")]
        result = compute_confidence(evidence=evidence, conflicts=[])
        assert "•" in result["reason"]

    def test_conflict_sets_conflicting_status(self):
        """Any conflict should set status to CONFLICTING."""
        evidence = [make_evidence("doc1"), make_evidence("doc2")]
        result = compute_confidence(
            evidence=evidence,
            conflicts=[make_conflict()]
        )
        assert result["status"] == AnswerStatus.CONFLICTING

    def test_factors_sum_within_range(self):
        """Sum of individual factors should not exceed 100."""
        evidence = [make_evidence(f"doc{i}", score=0.85) for i in range(4)]
        result = compute_confidence(evidence=evidence, conflicts=[])
        factors = result["factors"]
        total = sum(factors.values())
        assert 0 <= total <= 100

    def test_high_conflict_makes_uncertain(self):
        """Multiple high-severity conflicts should push confidence down significantly."""
        evidence = [make_evidence("doc1")]
        conflicts = [make_conflict(severity="HIGH") for _ in range(3)]
        result = compute_confidence(evidence=evidence, conflicts=conflicts)
        assert result["percent"] < 50


class TestClassifyAnswerState:

    def test_no_evidence_not_found(self):
        status = classify_answer_state([], [], "I cannot find this information.")
        assert status == AnswerStatus.NOT_FOUND

    def test_conflict_overrides(self):
        evidence = [make_evidence("doc1"), make_evidence("doc2")]
        conflicts = [make_conflict()]
        status = classify_answer_state(evidence, conflicts, "The deadline is 15 November 2026.")
        assert status == AnswerStatus.CONFLICTING

    def test_uncertainty_phrases_trigger_uncertain(self):
        evidence = [make_evidence("doc1")]
        answer = "The information is insufficient to determine the exact deadline."
        status = classify_answer_state(evidence, [], answer)
        assert status == AnswerStatus.UNCERTAIN

    def test_confident_answer_verified(self):
        evidence = [make_evidence("doc1"), make_evidence("doc2")]
        answer = "The project deadline is 15 November 2026 per Contract.pdf page 4."
        status = classify_answer_state(evidence, [], answer)
        assert status == AnswerStatus.VERIFIED

    def test_not_found_phrase(self):
        evidence = [make_evidence("doc1")]
        answer = "No evidence found in the uploaded documents."
        status = classify_answer_state(evidence, [], answer)
        assert status == AnswerStatus.UNCERTAIN
