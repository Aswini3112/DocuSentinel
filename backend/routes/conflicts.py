"""
DocuSentinel AI - Conflicts Route
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional

from backend.database import get_db
from backend.models.db_models import Conflict, ConflictSeverity, ConflictStatus, Document
from backend.models.schemas import ConflictResponse, ConflictListResponse

router = APIRouter()
logger = logging.getLogger("docusentinel.routes.conflicts")


class ConflictUpdateRequest(BaseModel):
    status: str
    resolution_note: Optional[str] = None


@router.get("", response_model=ConflictListResponse)
async def list_conflicts(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Conflict)
        .options(
            selectinload(Conflict.document_a),
            selectinload(Conflict.document_b),
        )
        .order_by(desc(Conflict.created_at))
    )

    if severity:
        try:
            sev = ConflictSeverity(severity.upper())
            query = query.where(Conflict.severity == sev)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")

    if status:
        try:
            st = ConflictStatus(status.lower())
            query = query.where(Conflict.status == st)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    result = await db.execute(query)
    conflicts = result.scalars().all()

    high   = sum(1 for c in conflicts if c.severity == ConflictSeverity.HIGH)
    medium = sum(1 for c in conflicts if c.severity == ConflictSeverity.MEDIUM)
    low    = sum(1 for c in conflicts if c.severity == ConflictSeverity.LOW)

    return ConflictListResponse(
        conflicts=[_to_response(c) for c in conflicts],
        total=len(conflicts),
        high=high,
        medium=medium,
        low=low,
    )


@router.get("/{conflict_id}", response_model=ConflictResponse)
async def get_conflict(conflict_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conflict)
        .options(
            selectinload(Conflict.document_a),
            selectinload(Conflict.document_b),
        )
        .where(Conflict.id == conflict_id)
    )
    conflict = result.scalar_one_or_none()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found.")
    return _to_response(conflict)


@router.patch("/{conflict_id}", response_model=ConflictResponse)
async def update_conflict(
    conflict_id: str,
    body: ConflictUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conflict)
        .options(
            selectinload(Conflict.document_a),
            selectinload(Conflict.document_b),
        )
        .where(Conflict.id == conflict_id)
    )
    conflict = result.scalar_one_or_none()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found.")

    try:
        conflict.status = ConflictStatus(body.status.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status '{body.status}'.")

    if body.resolution_note:
        conflict.description = (conflict.description or "") + f"\nResolution: {body.resolution_note}"

    await db.commit()
    await db.refresh(conflict)
    return _to_response(conflict)


def _to_response(conflict: Conflict) -> ConflictResponse:
    doc_a_name = conflict.document_a.original_name if conflict.document_a else "Unknown"
    doc_b_name = conflict.document_b.original_name if conflict.document_b else "Unknown"
    return ConflictResponse(
        id=conflict.id,
        field=conflict.field,
        document_a_name=doc_a_name,
        document_b_name=doc_b_name,
        document_a_id=conflict.document_a_id,
        document_b_id=conflict.document_b_id,
        value_a=conflict.value_a,
        value_b=conflict.value_b,
        severity=conflict.severity,
        status=conflict.status,
        description=conflict.description,
        created_at=conflict.created_at,
    )
