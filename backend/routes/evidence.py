"""
DocuSentinel AI - Evidence Route
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.db_models import DocumentChunk, Document, Claim, Conflict

router = APIRouter()
logger = logging.getLogger("docusentinel.routes.evidence")


@router.get("/{chunk_id}")
async def get_evidence_chunk(chunk_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DocumentChunk).where(DocumentChunk.id == chunk_id))
    chunk = result.scalar_one_or_none()
    if not chunk:
        raise HTTPException(status_code=404, detail="Evidence chunk not found.")

    doc_result = await db.execute(select(Document).where(Document.id == chunk.document_id))
    doc = doc_result.scalar_one_or_none()

    return {
        "chunk_id":      chunk.id,
        "document_id":   chunk.document_id,
        "document_name": doc.original_name if doc else "Unknown",
        "chunk_index":   chunk.chunk_index,
        "page_number":   chunk.page_number,
        "section":       chunk.section,
        "text":          chunk.text,
        "char_start":    chunk.char_start,
        "char_end":      chunk.char_end,
        "created_at":    chunk.created_at,
    }


@router.get("/document/{document_id}")
async def get_document_chunks(
    document_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    doc_result = await db.execute(select(Document).where(Document.id == document_id))
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    offset = (page - 1) * page_size
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .offset(offset)
        .limit(page_size)
    )
    chunks = result.scalars().all()

    return {
        "document_id":   document_id,
        "document_name": doc.original_name,
        "page":          page,
        "page_size":     page_size,
        "total_chunks":  doc.chunk_count,
        "chunks": [
            {
                "chunk_id":    c.id,
                "chunk_index": c.chunk_index,
                "page_number": c.page_number,
                "section":     c.section,
                "text":        c.text,
            }
            for c in chunks
        ],
    }


@router.get("/graph/data")
async def get_evidence_graph(db: AsyncSession = Depends(get_db)):
    """Return graph data for the Document Relation Graph."""
    docs_result = await db.execute(select(Document).where(Document.status == "ready"))
    documents = docs_result.scalars().all()

    claims_result = await db.execute(select(Claim))
    claims = claims_result.scalars().all()

    # Load conflicts without relationships — use raw IDs only
    conflicts_result = await db.execute(select(Conflict))
    conflicts = conflicts_result.scalars().all()

    # Build doc name lookup
    doc_names = {d.id: d.original_name for d in documents}

    nodes = []
    for doc in documents:
        nodes.append({
            "id":   f"doc_{doc.id}",
            "type": "document",
            "label": doc.original_name,
            "data": {
                "file_type":  doc.file_type,
                "page_count": doc.page_count,
                "is_demo":    doc.is_demo,
                "status":     doc.status,
            },
        })

    claim_node_map: dict[str, str] = {}
    claim_key_map: dict[str, str] = {}

    for claim in claims:
        key = f"{claim.field}:{claim.normalized_value or claim.raw_value}"
        if key not in claim_key_map:
            node_id = f"claim_{claim.id}"
            claim_key_map[key] = node_id
            nodes.append({
                "id":   node_id,
                "type": "claim",
                "label": f"{claim.field}: {claim.raw_value}",
                "data": {
                    "field":            claim.field,
                    "raw_value":        claim.raw_value,
                    "normalized_value": claim.normalized_value,
                    "page_number":      claim.page_number,
                },
            })
        claim_node_map[claim.id] = claim_key_map[key]

    edges = []
    edge_counter = 0

    for claim in claims:
        claim_node = claim_node_map.get(claim.id)
        if claim_node:
            edges.append({
                "id":     f"e{edge_counter}",
                "source": f"doc_{claim.document_id}",
                "target": claim_node,
                "label":  "mentions",
                "type":   "supports",
            })
            edge_counter += 1

    for conflict in conflicts:
        node_a = claim_node_map.get(conflict.claim_a_id)
        node_b = claim_node_map.get(conflict.claim_b_id)
        if node_a and node_b and node_a != node_b:
            edges.append({
                "id":       f"e{edge_counter}",
                "source":   node_a,
                "target":   node_b,
                "label":    "contradicts",
                "type":     "conflict",
                "severity": conflict.severity,
            })
            edge_counter += 1

    return {
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "documents": len(documents),
            "claims":    len(claim_key_map),
            "conflicts": len(conflicts),
        },
    }
