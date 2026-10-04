"""
DocuSentinel AI - Investigate Route
POST /api/investigate          — run a document investigation
GET  /api/investigations       — list past investigations
GET  /api/investigations/{id}  — get investigation detail
"""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.database import get_db
from backend.models.db_models import Investigation
from backend.models.schemas import (
    InvestigateRequest, InvestigateResponse,
    InvestigationListResponse, InvestigationListItem,
    EvidenceItem, SourceReference, InlineConflict,
)
from backend.services.investigator import run_investigation
from backend.services.llm_service import get_llm_status

router = APIRouter()
logger = logging.getLogger("docusentinel.routes.investigate")


@router.post("/investigate", response_model=InvestigateResponse)
async def investigate(
    request: InvestigateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run a full investigation. Returns answer + evidence + sources + conflicts + LLM status."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        response = await run_investigation(request, db)
        return response
    except Exception as e:
        logger.error(f"Investigation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Investigation failed: {str(e)}. "
                   "Ensure documents are uploaded and fully indexed."
        )


@router.get("/llm-status")
async def llm_status():
    """Quick endpoint the frontend polls to show AI provider status."""
    return get_llm_status()


@router.get("/investigations", response_model=InvestigationListResponse)
async def list_investigations(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Investigation)
        .order_by(desc(Investigation.created_at))
        .limit(limit)
    )
    investigations = result.scalars().all()
    items = [InvestigationListItem.model_validate(i) for i in investigations]
    return InvestigationListResponse(investigations=items, total=len(items))


@router.get("/investigations/{investigation_id}", response_model=InvestigateResponse)
async def get_investigation(
    investigation_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Investigation).where(Investigation.id == investigation_id)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found.")

    evidence, sources, conflicts = [], [], []
    try:
        if inv.evidence_json:
            evidence = [EvidenceItem(**e) for e in json.loads(inv.evidence_json)]
        if inv.sources_json:
            sources = [SourceReference(**s) for s in json.loads(inv.sources_json)]
        if inv.conflicts_json:
            conflicts = [InlineConflict(**c) for c in json.loads(inv.conflicts_json)]
    except Exception as parse_err:
        logger.warning(f"Failed to parse stored investigation JSON: {parse_err}")

    # llm_status stored in answer text prefix (legacy records won't have it)
    llm_info = get_llm_status()

    return InvestigateResponse(
        id=inv.id,
        question=inv.question,
        answer=inv.answer or "",
        answer_status=inv.answer_status,
        confidence_score=inv.confidence_score,
        confidence_percent=int(inv.confidence_score * 100),
        confidence_reason=inv.confidence_reason or "",
        evidence_strength=inv.evidence_strength or "None",
        has_conflict=inv.has_conflict,
        evidence=evidence,
        sources=sources,
        conflicts=conflicts,
        llm_used=False,                          # historical record — unknown
        llm_status=llm_info["status"],
        llm_status_msg=llm_info.get("message", ""),
        created_at=inv.created_at,
    )
