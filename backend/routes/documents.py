"""
DocuSentinel AI - Documents Route
POST /api/documents/upload   — upload and ingest a document
GET  /api/documents          — list all documents
GET  /api/documents/{id}     — get document details + sample chunks
DELETE /api/documents/{id}   — remove document
POST /api/documents/demo     — load demo documents
"""

import asyncio
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.database import get_db
from backend.config import get_settings
from backend.models.db_models import Document, DocumentChunk, DocumentStatus, DocumentType
from backend.models.schemas import (
    DocumentResponse, DocumentListResponse, DocumentDetailResponse
)
from backend.services.ingestion import ingest_document
from backend.services.vector_store import get_vector_store
from backend.utils.file_utils import (
    validate_file_extension, get_file_type, safe_filename, compute_file_hash
)

router = APIRouter()
logger = logging.getLogger("docusentinel.routes.documents")
settings = get_settings()


# ─────────────────────────────────────────────
# Upload
# ─────────────────────────────────────────────

@router.post("/upload", response_model=DocumentResponse, status_code=http_status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept a document upload, save it to disk, create a DB record,
    and kick off background ingestion.
    Returns immediately with status=uploading.
    """
    # Validate file extension
    if not validate_file_extension(file.filename):
        raise HTTPException(
            status_code=http_status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Allowed: PDF, DOCX, TXT, PNG, JPG, TIFF, BMP.",
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.max_file_size_mb} MB.",
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    file_type = get_file_type(file.filename)
    stored_name = safe_filename(file.filename)
    file_hash = compute_file_hash(content)

    # Check for duplicate file
    existing = await db.execute(
        select(Document).where(Document.file_hash == file_hash)
    )
    dup = existing.scalar_one_or_none()
    if dup and dup.status == DocumentStatus.READY:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"This document has already been uploaded as '{dup.original_name}'.",
        )

    # Save file to disk
    save_path = settings.upload_path / stored_name
    with open(save_path, "wb") as f:
        f.write(content)

    # Create DB record
    doc = Document(
        original_name=file.filename,
        stored_name=stored_name,
        file_type=file_type,
        file_size=len(content),
        file_hash=file_hash,
        status=DocumentStatus.UPLOADING,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Kick off ingestion in background
    background_tasks.add_task(_run_ingestion, doc.id)

    logger.info(f"Document queued for ingestion: {file.filename} ({file_type}, {len(content)} bytes)")
    return DocumentResponse.model_validate(doc)


async def _run_ingestion(document_id: str):
    """Background task: runs the ingestion pipeline with its own DB session."""
    from backend.database import AsyncSessionLocal
    from backend.services.conflict_engine import detect_conflicts_for_document

    async with AsyncSessionLocal() as session:
        try:
            await ingest_document(document_id, session)
            # After ingestion, run conflict detection against other documents
            await detect_conflicts_for_document(document_id, session)
        except Exception as e:
            logger.error(f"Background ingestion failed for {document_id}: {e}")


# ─────────────────────────────────────────────
# List
# ─────────────────────────────────────────────

@router.get("", response_model=DocumentListResponse)
async def list_documents(db: AsyncSession = Depends(get_db)):
    """Return all documents ordered by upload time (newest first)."""
    result = await db.execute(
        select(Document).order_by(desc(Document.created_at))
    )
    docs = result.scalars().all()
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=len(docs),
    )


# ─────────────────────────────────────────────
# Detail
# ─────────────────────────────────────────────

@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Return document details including sample chunks."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Fetch sample chunks (first 5)
    chunks_result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .limit(5)
    )
    sample_chunks = [
        {
            "chunk_index": c.chunk_index,
            "page_number": c.page_number,
            "section": c.section,
            "text": c.text[:300] + "…" if len(c.text) > 300 else c.text,
        }
        for c in chunks_result.scalars().all()
    ]

    response = DocumentDetailResponse.model_validate(doc)
    response.sample_chunks = sample_chunks
    return response


# ─────────────────────────────────────────────
# Delete
# ─────────────────────────────────────────────

@router.delete("/{document_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a document, its chunks, claims, and vectors."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Remove from vector store
    vector_store = get_vector_store()
    vector_store.delete_document(document_id)

    # Remove file from disk
    file_path = settings.upload_path / doc.stored_name
    if file_path.exists():
        file_path.unlink()

    # Cascade delete in DB (chunks + claims deleted via ORM cascade)
    await db.delete(doc)
    await db.commit()
    logger.info(f"Document deleted: {doc.original_name}")


# ─────────────────────────────────────────────
# Load Demo Documents
# ─────────────────────────────────────────────

@router.post("/demo/load", status_code=http_status.HTTP_202_ACCEPTED)
async def load_demo_documents(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Load all demo documents from /data/demo into the system.
    These synthetic documents contain intentional contradictions for demonstration.
    """
    demo_dir = Path(__file__).parent.parent.parent / "data" / "demo"
    if not demo_dir.exists():
        raise HTTPException(status_code=404, detail="Demo data directory not found.")

    demo_files = list(demo_dir.glob("*.txt")) + list(demo_dir.glob("*.pdf"))
    if not demo_files:
        raise HTTPException(status_code=404, detail="No demo files found in /data/demo.")

    queued = []
    for demo_file in demo_files:
        content = demo_file.read_bytes()
        file_type = get_file_type(demo_file.name)
        stored_name = safe_filename(demo_file.name)
        file_hash = compute_file_hash(content)

        # Skip if already loaded
        existing = await db.execute(
            select(Document).where(Document.file_hash == file_hash)
        )
        if existing.scalar_one_or_none():
            continue

        # Copy to upload dir
        save_path = settings.upload_path / stored_name
        with open(save_path, "wb") as f:
            f.write(content)

        doc = Document(
            original_name=demo_file.name,
            stored_name=stored_name,
            file_type=file_type,
            file_size=len(content),
            file_hash=file_hash,
            status=DocumentStatus.UPLOADING,
            is_demo=True,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        background_tasks.add_task(_run_ingestion, doc.id)
        queued.append(demo_file.name)

    return {
        "message": f"Demo documents queued for ingestion: {len(queued)} files.",
        "files": queued,
    }
