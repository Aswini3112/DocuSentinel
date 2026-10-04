"""
DocuSentinel AI - Evidence Retrieval Service
Takes a natural-language question, embeds it, queries the vector store,
and returns ranked evidence chunks with full source metadata.
"""

import logging
from typing import Optional
from backend.config import get_settings
from backend.services.embedder import embed_query
from backend.services.vector_store import get_vector_store
from backend.models.schemas import EvidenceItem

logger = logging.getLogger("docusentinel.retrieval")
settings = get_settings()


def retrieve_evidence(
    question: str,
    top_k: Optional[int] = None,
    document_ids: Optional[list[str]] = None,
    min_score: Optional[float] = None,
) -> list[EvidenceItem]:
    """
    Core retrieval function.

    1. Embeds the question.
    2. Queries the vector store for top_k nearest chunks.
    3. Filters by minimum relevance score.
    4. Returns EvidenceItem list sorted by relevance.

    Args:
        question:     Natural language query
        top_k:        Number of chunks to retrieve (default from config)
        document_ids: Optional filter to specific document IDs
        min_score:    Minimum cosine similarity (0–1) to include a result

    Returns:
        List of EvidenceItem sorted by relevance_score descending.
    """
    effective_top_k   = top_k    if top_k    is not None else settings.top_k_retrieval
    effective_min     = min_score if min_score is not None else settings.similarity_threshold

    logger.info(f"Retrieving evidence for: '{question[:80]}...' "
                f"(top_k={effective_top_k}, min_score={effective_min})")

    # Embed the query
    try:
        query_vector = embed_query(question)
    except Exception as e:
        logger.error(f"Query embedding failed: {e}")
        return []

    if not query_vector:
        logger.warning("Empty query embedding — returning no evidence.")
        return []

    # Query vector store
    vector_store = get_vector_store()
    raw_results = vector_store.query(
        query_embedding=query_vector,
        top_k=effective_top_k,
        document_ids=document_ids,
        min_score=effective_min,
    )

    if not raw_results:
        logger.info("No relevant evidence found above threshold.")
        return []

    # Convert to EvidenceItem schema
    evidence_items: list[EvidenceItem] = []
    for r in raw_results:
        evidence_items.append(EvidenceItem(
            chunk_id=r["chunk_id"],
            document_id=r["document_id"],
            document_name=r["document_name"],
            page_number=r["page_number"],
            section=r.get("section"),
            text=r["text"],
            relevance_score=r["relevance_score"],
        ))

    logger.info(f"Retrieved {len(evidence_items)} evidence chunks.")
    return evidence_items


def deduplicate_evidence(items: list[EvidenceItem]) -> list[EvidenceItem]:
    """
    Remove near-duplicate evidence items.
    Two items are considered duplicates if they share the same document_id
    and their text overlap is > 80%.
    """
    if len(items) <= 1:
        return items

    unique: list[EvidenceItem] = []
    for candidate in items:
        is_dup = False
        for existing in unique:
            if existing.document_id == candidate.document_id:
                overlap = _text_overlap_ratio(candidate.text, existing.text)
                if overlap > 0.8:
                    is_dup = True
                    break
        if not is_dup:
            unique.append(candidate)

    return unique


def build_source_references(evidence: list[EvidenceItem]) -> list[dict]:
    """
    Collapse evidence items into unique source references grouped by
    (document_id, page_number, section) for display in the UI.
    """
    seen = set()
    sources = []

    for item in evidence:
        key = (item.document_id, item.page_number, item.section)
        if key not in seen:
            seen.add(key)
            sources.append({
                "document_id":   item.document_id,
                "document_name": item.document_name,
                "page_number":   item.page_number,
                "section":       item.section,
                "excerpt":       item.text[:200] + "…" if len(item.text) > 200 else item.text,
            })

    return sources


def _text_overlap_ratio(a: str, b: str) -> float:
    """
    Simple overlap ratio between two strings based on shared word sets.
    Returns value between 0.0 and 1.0.
    """
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)
