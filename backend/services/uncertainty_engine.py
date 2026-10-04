"""
DocuSentinel AI - Uncertainty Engine
Calculates transparent, explainable confidence scores.
Classifies every answer into one of four states:
  VERIFIED | CONFLICTING | UNCERTAIN | NOT_FOUND

The score is intentionally heuristic and labeled as such in the UI.
"""

import logging
from backend.models.schemas import EvidenceItem, InlineConflict
from backend.models.db_models import AnswerStatus

logger = logging.getLogger("docusentinel.uncertainty")


def compute_confidence(
    evidence: list[EvidenceItem],
    conflicts: list[InlineConflict],
    question: str = "",
) -> dict:
    """
    Compute an evidence-based confidence score and answer status.

    Scoring factors (weights):
    - Retrieval relevance (avg score of top evidence)   → 0–40 pts
    - Number of supporting sources (unique docs)         → 0–20 pts
    - Source agreement (no conflicts)                    → 0–25 pts
    - Evidence completeness (chunk count)                → 0–15 pts

    Returns:
    {
        "score":            float (0.0–1.0),
        "percent":          int (0–100),
        "status":           AnswerStatus,
        "evidence_strength": str ("High" | "Medium" | "Low" | "None"),
        "reason":           str (human-readable explanation),
        "factors":          dict (individual factor contributions),
    }
    """
    # ── No evidence at all ───────────────────────────────────────────────
    if not evidence:
        return {
            "score":            0.0,
            "percent":          0,
            "status":           AnswerStatus.NOT_FOUND,
            "evidence_strength": "None",
            "reason":           "No relevant evidence found in the uploaded documents.",
            "factors": {
                "retrieval_relevance": 0,
                "source_count":        0,
                "source_agreement":    0,
                "completeness":        0,
            },
        }

    # ── Factor 1: Retrieval relevance ────────────────────────────────────
    # Average relevance of top-3 evidence chunks (normalized 0→40 pts)
    top_scores = sorted([e.relevance_score for e in evidence], reverse=True)[:3]
    avg_relevance = sum(top_scores) / len(top_scores)
    relevance_pts = int(avg_relevance * 40)

    # ── Factor 2: Source count (unique documents) ────────────────────────
    unique_docs = len(set(e.document_id for e in evidence))
    source_pts = min(unique_docs * 10, 20)  # 10 per doc, max 20

    # ── Factor 3: Source agreement (conflict penalty) ────────────────────
    if conflicts:
        high_severity = sum(1 for c in conflicts if c.severity == "HIGH")
        med_severity  = sum(1 for c in conflicts if c.severity == "MEDIUM")
        # Heavy penalty for high severity conflicts
        penalty = (high_severity * 15) + (med_severity * 8)
        agreement_pts = max(0, 25 - penalty)
    else:
        agreement_pts = 25  # Full score — sources agree

    # ── Factor 4: Evidence completeness ─────────────────────────────────
    # Reward having multiple chunks; cap at 15 pts
    chunk_count = len(evidence)
    completeness_pts = min(chunk_count * 3, 15)

    # ── Total score ──────────────────────────────────────────────────────
    raw_score = relevance_pts + source_pts + agreement_pts + completeness_pts
    # raw_score is out of 100, clamp to [0, 100]
    final_score_pct = max(0, min(100, raw_score))
    final_score = final_score_pct / 100.0

    # ── Determine answer status ──────────────────────────────────────────
    if conflicts:
        status = AnswerStatus.CONFLICTING
    elif final_score_pct >= 70:
        status = AnswerStatus.VERIFIED
    elif final_score_pct >= 35:
        status = AnswerStatus.UNCERTAIN
    else:
        status = AnswerStatus.UNCERTAIN

    # ── Evidence strength label ──────────────────────────────────────────
    if final_score_pct >= 75:
        strength = "High"
    elif final_score_pct >= 45:
        strength = "Medium"
    elif final_score_pct > 0:
        strength = "Low"
    else:
        strength = "None"

    # ── Human-readable reason ─────────────────────────────────────────────
    reason = _build_reason(
        avg_relevance=avg_relevance,
        unique_docs=unique_docs,
        conflicts=conflicts,
        chunk_count=chunk_count,
        final_score_pct=final_score_pct,
    )

    result = {
        "score":             round(final_score, 4),
        "percent":           final_score_pct,
        "status":            status,
        "evidence_strength": strength,
        "reason":            reason,
        "factors": {
            "retrieval_relevance": relevance_pts,
            "source_count":        source_pts,
            "source_agreement":    agreement_pts,
            "completeness":        completeness_pts,
        },
    }

    logger.info(
        f"Confidence: {final_score_pct}% | Status: {status} | "
        f"Strength: {strength} | Conflicts: {len(conflicts)}"
    )
    return result


def _build_reason(
    avg_relevance: float,
    unique_docs: int,
    conflicts: list[InlineConflict],
    chunk_count: int,
    final_score_pct: int,
) -> str:
    """Build a bullet-point explanation of the confidence score."""
    bullets = []

    # Relevance
    if avg_relevance >= 0.75:
        bullets.append("High retrieval relevance — retrieved chunks closely match the question.")
    elif avg_relevance >= 0.5:
        bullets.append("Moderate retrieval relevance — some chunks are closely related.")
    else:
        bullets.append("Low retrieval relevance — retrieved evidence may be loosely related.")

    # Source count
    if unique_docs >= 3:
        bullets.append(f"Strong multi-source support — {unique_docs} documents contribute evidence.")
    elif unique_docs == 2:
        bullets.append("Two documents provide supporting evidence.")
    else:
        bullets.append("Only one document provides supporting evidence.")

    # Conflicts
    if conflicts:
        high = sum(1 for c in conflicts if c.severity == "HIGH")
        med  = sum(1 for c in conflicts if c.severity == "MEDIUM")
        if high > 0:
            bullets.append(f"⚠ {high} high-severity conflict(s) detected — sources disagree on critical values.")
        if med > 0:
            bullets.append(f"⚠ {med} medium-severity conflict(s) detected.")
        bullets.append("Confidence reduced due to contradictory evidence.")
    else:
        if unique_docs > 1:
            bullets.append("All sources are consistent — no contradictions found.")

    # Completeness
    if chunk_count >= 4:
        bullets.append(f"Good evidence density — {chunk_count} supporting chunks retrieved.")
    elif chunk_count == 1:
        bullets.append("Limited evidence — only 1 supporting chunk found.")

    return "\n".join(f"• {b}" for b in bullets)


def classify_answer_state(
    evidence: list[EvidenceItem],
    conflicts: list[InlineConflict],
    answer_text: str,
) -> AnswerStatus:
    """
    Final classification of the answer state.
    Checks answer text for uncertainty signals as a secondary indicator.
    """
    if not evidence:
        return AnswerStatus.NOT_FOUND

    if conflicts:
        return AnswerStatus.CONFLICTING

    # Check if the LLM itself expressed uncertainty
    uncertainty_phrases = [
        "insufficient", "unclear", "cannot determine", "not found",
        "no evidence", "not mentioned", "unable to", "not available",
        "does not specify", "no information",
    ]
    answer_lower = answer_text.lower()
    if any(phrase in answer_lower for phrase in uncertainty_phrases):
        return AnswerStatus.UNCERTAIN

    return AnswerStatus.VERIFIED
