"""
DocuSentinel AI - Document Ingestion Pipeline
Orchestrates: upload → extract → chunk → embed → store → index claims.
Called by the documents route after a file is saved to disk.
"""

import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config import get_settings
from backend.models.db_models import Document, DocumentChunk, Claim, DocumentStatus
from backend.services.extractor import extract_document
from backend.services.chunker import chunk_pages
from backend.services.embedder import embed_texts
from backend.services.vector_store import get_vector_store
from backend.services.claim_extractor import extract_claims_from_chunks
from backend.utils.text_utils import clean_text

logger = logging.getLogger("docusentinel.ingestion")
settings = get_settings()


async def ingest_document(document_id: str, db: AsyncSession) -> None:
    """
    Full ingestion pipeline for a document that has already been saved to disk.
    Updates document status in the DB at each stage.
    """
    # Load document record
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        logger.error(f"Document {document_id} not found in DB.")
        return

    file_path = str(settings.upload_path / doc.stored_name)

    async def set_status(status: DocumentStatus, error: str = None):
        doc.status = status
        if error:
            doc.error_message = error
        await db.commit()

    try:
        # ── Stage 1: Extract ────────────────────────────────────────────
        await set_status(DocumentStatus.EXTRACTING)
        logger.info(f"[{doc.original_name}] Extracting text...")

        extraction = extract_document(file_path, doc.file_type)

        if not extraction.success:
            await set_status(DocumentStatus.FAILED, extraction.error)
            logger.error(f"[{doc.original_name}] Extraction failed: {extraction.error}")
            return

        doc.page_count = extraction.total_pages
        await db.commit()

        # ── Stage 2: Chunk ───────────────────────────────────────────────
        await set_status(DocumentStatus.INDEXING)
        logger.info(f"[{doc.original_name}] Chunking {extraction.total_pages} pages...")

        chunks = chunk_pages(
            pages=extraction.pages,
            document_id=document_id,
            document_name=doc.original_name,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

        if not chunks:
            await set_status(DocumentStatus.FAILED, "Chunking produced no content.")
            return

        # ── Stage 3: Save chunks to DB ───────────────────────────────────
        db_chunks: list[DocumentChunk] = []
        for chunk in chunks:
            db_chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                page_number=chunk.page_number,
                section=chunk.section,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
            )
            db.add(db_chunk)
            db_chunks.append(db_chunk)

        await db.commit()

        # Refresh to get assigned IDs
        for db_chunk in db_chunks:
            await db.refresh(db_chunk)

        doc.chunk_count = len(db_chunks)
        await db.commit()

        # ── Stage 4: Embed + Store in vector DB ─────────────────────────
        logger.info(f"[{doc.original_name}] Generating embeddings for {len(chunks)} chunks...")

        texts = [c.text for c in chunks]
        embeddings = embed_texts(texts)

        if not embeddings or len(embeddings) != len(chunks):
            await set_status(DocumentStatus.FAILED, "Embedding generation failed.")
            return

        # Build metadata list for vector store
        metadatas = []
        ids = []
        for db_chunk, chunk in zip(db_chunks, chunks):
            metadatas.append({
                "chunk_id":      db_chunk.id,
                "document_id":   document_id,
                "document_name": doc.original_name,
                "page_number":   chunk.page_number,
                "section":       chunk.section or "",
                "chunk_index":   chunk.chunk_index,
            })
            ids.append(db_chunk.id)

        vector_store = get_vector_store()
        vector_store.add_embeddings(
            ids=ids,
            embeddings=embeddings,
            texts=texts,
            metadatas=metadatas,
        )

        logger.info(f"[{doc.original_name}] Vectors stored.")

        # ── Stage 5: Extract Claims ──────────────────────────────────────
        logger.info(f"[{doc.original_name}] Extracting factual claims...")

        claims_data = extract_claims_from_chunks(chunks, document_id=document_id)

        for claim_data in claims_data:
            # Find the matching db_chunk by chunk_index
            matching_chunk = next(
                (c for c in db_chunks if c.chunk_index == claim_data.get("chunk_index")),
                None,
            )
            claim = Claim(
                document_id=document_id,
                chunk_id=matching_chunk.id if matching_chunk else None,
                field=claim_data["field"],
                raw_value=claim_data["raw_value"],
                normalized_value=claim_data.get("normalized_value"),
                page_number=claim_data.get("page_number", 0),
                context_text=claim_data.get("context_text"),
            )
            db.add(claim)

        await db.commit()
        logger.info(f"[{doc.original_name}] {len(claims_data)} claims extracted.")

        # ── Done ─────────────────────────────────────────────────────────
        await set_status(DocumentStatus.READY)
        logger.info(f"[{doc.original_name}] Ingestion complete. "
                    f"{doc.page_count} pages, {doc.chunk_count} chunks, "
                    f"{len(claims_data)} claims.")

    except Exception as e:
        logger.exception(f"[{doc.original_name}] Ingestion pipeline error: {e}")
        await set_status(DocumentStatus.FAILED, str(e))
