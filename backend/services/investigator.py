"""
DocuSentinel AI - Investigation Orchestrator
retrieve → conflict-detect → RAG/LLM → uncertainty → persist → respond
"""

import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.db_models import Investigation, AnswerStatus
from backend.models.schemas import (
    InvestigateRequest, InvestigateResponse,
    EvidenceItem, SourceReference, InlineConflict,
)
from backend.services.retrieval import retrieve_evidence, deduplicate_evidence, build_source_references
from backend.services.conflict_engine import detect_inline_conflicts, build_conflict_summary
from backend.services.rag_engine import generate_answer
from backend.services.uncertainty_engine import compute_confidence, classify_answer_state

logger = logging.getLogger("docusentinel.investigator")
settings = get_settings()


async def run_investigation(
    request: InvestigateRequest,
    db: AsyncSession,
) -> InvestigateResponse:
    logger.info(f"Investigation started: '{request.question[:80]}'")

    # ── 1. Retrieve evidence ──────────────────────────────────────────────
    raw_evidence = retrieve_evidence(
        question=request.question,
        document_ids=request.document_ids,
    )
    evidence = deduplicate_evidence(raw_evidence)
    logger.info(f"Retrieved {len(evidence)} evidence chunks")

    # ── 2. Detect inline conflicts ────────────────────────────────────────
    inline_conflicts = detect_inline_conflicts(evidence)
    has_conflict = len(inline_conflicts) > 0
    conflict_summary = build_conflict_summary(inline_conflicts)

    # ── 3. Generate answer (LLM or evidence-only) ─────────────────────────
    answer_result = generate_answer(
        question=request.question,
        evidence=evidence,
        has_conflict=has_conflict,
        conflict_summary=conflict_summary,
    )
    answer_text   = answer_result["answer"]
    llm_used      = answer_result["llm_used"]
    llm_status    = answer_result["llm_status"]
    llm_status_msg = answer_result["llm_status_msg"]

    # ── 4. Confidence + status ────────────────────────────────────────────
    confidence = compute_confidence(
        evidence=evidence,
        conflicts=inline_conflicts,
        question=request.question,
    )

    # If LLM returned its own status/confidence, trust it (it saw the evidence)
    if llm_used and answer_result.get("ai_status"):
        llm_status_str = answer_result["ai_status"]
        try:
            final_status = AnswerStatus(llm_status_str)
        except ValueError:
            final_status = classify_answer_state(evidence, inline_conflicts, answer_text)
        # Blend LLM confidence with heuristic (weighted average)
        llm_conf = answer_result.get("ai_confidence") or confidence["percent"]
        blended = int(0.6 * llm_conf + 0.4 * confidence["percent"])
        confidence["percent"] = blended
        confidence["score"] = round(blended / 100, 4)
    else:
        final_status = classify_answer_state(evidence, inline_conflicts, answer_text)

    # ── 5. Source references ──────────────────────────────────────────────
    source_dicts = build_source_references(evidence)
    sources = [SourceReference(**s) for s in source_dicts]

    # ── 6. Persist ────────────────────────────────────────────────────────
    investigation = Investigation(
        question=request.question,
        answer=answer_text,
        answer_status=final_status,
        confidence_score=confidence["score"],
        confidence_reason=confidence["reason"],
        evidence_strength=confidence["evidence_strength"],
        has_conflict=has_conflict,
        evidence_json=json.dumps([e.model_dump() for e in evidence]),
        sources_json=json.dumps([s.model_dump() for s in sources]),
        conflicts_json=json.dumps([c.model_dump() for c in inline_conflicts]),
    )
    db.add(investigation)
    await db.commit()
    await db.refresh(investigation)

    logger.info(
        f"Investigation complete: status={final_status}, "
        f"confidence={confidence['percent']}%, llm={llm_used}, "
        f"evidence={len(evidence)}, conflicts={len(inline_conflicts)}"
    )

    return InvestigateResponse(
        id=investigation.id,
        question=request.question,
        answer=answer_text,
        answer_status=final_status,
        confidence_score=confidence["score"],
        confidence_percent=confidence["percent"],
        confidence_reason=confidence["reason"],
        evidence_strength=confidence["evidence_strength"],
        has_conflict=has_conflict,
        evidence=evidence,
        sources=sources,
        conflicts=inline_conflicts,
        llm_used=llm_used,
        llm_status=llm_status,
        llm_status_msg=llm_status_msg,
        created_at=investigation.created_at,
    )
