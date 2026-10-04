"""
DocuSentinel AI - RAG Answer Engine
Uses llm_service.py for real LLM calls (any OpenAI-compatible provider).
Honest fallback: when LLM is not configured, returns evidence-only answer
with a clear NOT_CONFIGURED marker — never pretends AI is running.
"""

import logging
from backend.config import get_settings
from backend.models.schemas import EvidenceItem
from backend.services.llm_service import (
    call_llm_for_investigation,
    LLMNotConfiguredError,
    LLMCallError,
    get_llm_status,
)

logger = logging.getLogger("docusentinel.rag")
settings = get_settings()


def _build_evidence_context(evidence: list[EvidenceItem]) -> str:
    if not evidence:
        return "NO EVIDENCE RETRIEVED.\n"
    lines = ["=== RETRIEVED EVIDENCE ===\n"]
    for i, item in enumerate(evidence, 1):
        sec = f" | Section: {item.section}" if item.section else ""
        lines.append(
            f"[Evidence {i}]\n"
            f"Source: {item.document_name} | Page {item.page_number}{sec}\n"
            f"Relevance: {item.relevance_score:.0%}\n"
            f"Text: {item.text}\n"
        )
    return "\n".join(lines)


def _build_conflict_note(has_conflict: bool, conflict_summary: str) -> str:
    if not has_conflict or not conflict_summary:
        return ""
    return (
        f"\n\n⚠ CONFLICT ALERT — the following contradictions were detected:\n"
        f"{conflict_summary}\n"
        "Present ALL versions explicitly. Do NOT resolve or choose one. Label as CONFLICTING.\n"
    )


def generate_answer(
    question: str,
    evidence: list[EvidenceItem],
    has_conflict: bool = False,
    conflict_summary: str = "",
) -> dict:
    """
    Generate a grounded answer.

    Returns dict with keys:
      answer        — str
      llm_used      — bool  (True = real LLM, False = evidence-only fallback)
      llm_status    — str   (CONFIGURED / NOT_CONFIGURED / ERROR)
      lm_status_msg — str   (human-readable explanation)
      ai_status     — str   (VERIFIED / CONFLICTING / UNCERTAIN / NOT_FOUND) from LLM if used
      ai_confidence — int   (0-100, LLM-provided if available)
    """
    evidence_context = _build_evidence_context(evidence)
    conflict_note = _build_conflict_note(has_conflict, conflict_summary)

    # ── Try real LLM ──────────────────────────────────────────────────────
    try:
        result = call_llm_for_investigation(
            question=question,
            evidence_context=evidence_context,
            conflict_note=conflict_note,
        )
        logger.info(
            f"LLM answer: status={result['status']}, "
            f"confidence={result['confidence']}%"
        )
        return {
            "answer":         result["answer"],
            "llm_used":       True,
            "llm_status":     "CONFIGURED",
            "llm_status_msg": f"Model: {settings.llm_model}",
            "ai_status":      result["status"],
            "ai_confidence":  result["confidence"],
            "reasoning":      result.get("reasoning_summary", ""),
        }

    except LLMNotConfiguredError as e:
        logger.info("LLM not configured — using evidence-only fallback.")
        answer = _evidence_only_answer(question, evidence, has_conflict, conflict_summary)
        return {
            "answer":         answer,
            "llm_used":       False,
            "llm_status":     "NOT_CONFIGURED",
            "llm_status_msg": str(e),
            "ai_status":      None,   # determined by uncertainty_engine, not LLM
            "ai_confidence":  None,
            "reasoning":      "",
        }

    except LLMCallError as e:
        logger.error(f"LLM call error: {e}")
        answer = _evidence_only_answer(question, evidence, has_conflict, conflict_summary)
        return {
            "answer":         answer,
            "llm_used":       False,
            "llm_status":     "ERROR",
            "llm_status_msg": str(e),
            "ai_status":      None,
            "ai_confidence":  None,
            "reasoning":      "",
        }


def _evidence_only_answer(
    question: str,
    evidence: list[EvidenceItem],
    has_conflict: bool,
    conflict_summary: str,
) -> str:
    """
    Build a transparent, evidence-only answer when LLM is unavailable.
    Never invents data — only quotes what was retrieved.
    Clearly labels that AI reasoning is not active.
    """
    lines = [
        "ℹ️  AI REASONING NOT ACTIVE",
        "─────────────────────────────────────────────────────",
        "No LLM API key is configured. The answer below is built",
        "directly from retrieved document evidence without AI reasoning.",
        "Configure LLM_API_KEY in backend/.env for full AI-powered answers.",
        "",
    ]

    if not evidence:
        lines += [
            "❌ NOT FOUND",
            "",
            "No relevant evidence was found in the uploaded documents.",
            "Upload documents and ensure they are fully indexed before investigating.",
        ]
        return "\n".join(lines)

    if has_conflict:
        lines += [
            "⚠️  CONTRADICTION DETECTED ACROSS DOCUMENTS",
            "",
            "The following conflicting claims were found:",
        ]
        for c_line in conflict_summary.split("\n"):
            if c_line.strip():
                lines.append(f"  • {c_line.strip()}")
        lines.append("")

    lines.append("SUPPORTING EVIDENCE:")
    lines.append("")
    for i, item in enumerate(evidence[:8], 1):
        sec = f" — {item.section}" if item.section else ""
        lines.append(f"[{i}] {item.document_name}  |  Page {item.page_number}{sec}")
        excerpt = item.text[:500] + ("…" if len(item.text) > 500 else "")
        lines.append(f'    "{excerpt}"')
        lines.append("")

    if len(evidence) > 8:
        lines.append(f"… and {len(evidence) - 8} additional supporting chunk(s).")

    return "\n".join(lines)
