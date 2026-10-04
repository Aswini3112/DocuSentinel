"""
DocuSentinel AI - Health Route
GET /api/health — real subsystem status, never lies about LLM state
GET /api/stats  — dashboard statistics from actual database
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.database import get_db
from backend.config import get_settings
from backend.models.db_models import Document, DocumentStatus, Conflict, Investigation, Claim, AnswerStatus
from backend.models.schemas import HealthResponse, DashboardStats
from backend.services.vector_store import get_vector_store
from backend.services.llm_service import get_llm_status

router = APIRouter()
logger = logging.getLogger("docusentinel.routes.health")
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    # ── Database ──────────────────────────────────────────────────────────
    try:
        await db.execute(select(func.count()).select_from(Document))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    # ── Vector store ──────────────────────────────────────────────────────
    try:
        vs = get_vector_store()
        vs_health = vs.health_check()
        vs_status = f"ok ({vs_health['vectors']} vectors)"
    except Exception as e:
        vs_status = f"error: {e}"

    # ── LLM — honest status, never claims ONLINE when not configured ──────
    llm_info = get_llm_status()
    llm_status = llm_info["status"]       # NOT_CONFIGURED | CONFIGURED | ERROR
    llm_model  = llm_info.get("model")
    llm_msg    = llm_info.get("message", "")

    # Human-readable llm string for legacy field
    if llm_status == "NOT_CONFIGURED":
        llm_display = "NOT CONFIGURED — add LLM_API_KEY to backend/.env"
    elif llm_status == "CONFIGURED":
        llm_display = f"CONFIGURED — {llm_model}"
    else:
        llm_display = f"ERROR — {llm_msg}"

    overall = "ok" if "error" not in db_status else "degraded"

    return HealthResponse(
        status=overall,
        app=settings.app_name,
        version=settings.app_version,
        database=db_status,
        vector_store=vs_status,
        llm=llm_display,
        llm_status=llm_status,
        llm_model=llm_model,
        llm_message=llm_msg,
    )


@router.get("/stats", response_model=DashboardStats)
async def get_stats(db: AsyncSession = Depends(get_db)):
    # Documents analyzed (status = ready)
    doc_count = await db.execute(
        select(func.count()).select_from(Document)
        .where(Document.status == DocumentStatus.READY)
    )
    documents_analyzed = doc_count.scalar() or 0

    # Claims extracted
    claim_count = await db.execute(select(func.count()).select_from(Claim))
    claims_extracted = claim_count.scalar() or 0

    # Conflicts detected
    conflict_count = await db.execute(select(func.count()).select_from(Conflict))
    conflicts_detected = conflict_count.scalar() or 0

    # Uncertain / NOT_FOUND investigations
    uncertain_count = await db.execute(
        select(func.count()).select_from(Investigation)
        .where(Investigation.answer_status.in_([
            AnswerStatus.UNCERTAIN, AnswerStatus.NOT_FOUND
        ]))
    )
    uncertain_claims = uncertain_count.scalar() or 0

    # Average confidence
    avg_conf = await db.execute(
        select(func.avg(Investigation.confidence_score)).select_from(Investigation)
    )
    avg_confidence = float(avg_conf.scalar() or 0.0) * 100

    # Evidence coverage
    total_inv_r = await db.execute(select(func.count()).select_from(Investigation))
    total_investigations = total_inv_r.scalar() or 0

    evidenced_inv = await db.execute(
        select(func.count()).select_from(Investigation)
        .where(Investigation.answer_status.in_([
            AnswerStatus.VERIFIED, AnswerStatus.CONFLICTING
        ]))
    )
    evidenced = evidenced_inv.scalar() or 0
    evidence_coverage = (evidenced / total_investigations * 100) if total_investigations > 0 else 0.0

    # Conflict risk
    conflicted = await db.execute(
        select(func.count()).select_from(Investigation)
        .where(Investigation.has_conflict == True)
    )
    conflicted_count = conflicted.scalar() or 0
    conflict_risk = (conflicted_count / total_investigations * 100) if total_investigations > 0 else 0.0

    return DashboardStats(
        documents_analyzed=documents_analyzed,
        claims_extracted=claims_extracted,
        conflicts_detected=conflicts_detected,
        uncertain_claims=uncertain_claims,
        evidence_coverage=round(evidence_coverage, 1),
        answer_confidence=round(avg_confidence, 1),
        conflict_risk=round(conflict_risk, 1),
    )
