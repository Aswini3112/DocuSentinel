"""
DocuSentinel AI - Vector Store (Pure NumPy in-process store)
No chromadb required. Stores embeddings as numpy arrays on disk (.npz).
Fast enough for hackathon demo scale (< 50k chunks).
"""

import json
import logging
import numpy as np
from pathlib import Path
from typing import Optional
from backend.config import get_settings

logger = logging.getLogger("docusentinel.vectorstore")
settings = get_settings()

VECTORS_FILE  = "vectors.npz"
METADATA_FILE = "metadata.json"


class VectorStore:
    """
    In-process vector store backed by numpy arrays saved to disk.
    Supports upsert, cosine similarity query, and delete by document_id.
    """

    def __init__(self):
        self._ids:       list[str]        = []
        self._texts:     list[str]        = []
        self._metadatas: list[dict]       = []
        self._matrix:    Optional[np.ndarray] = None  # shape (N, D)
        self._loaded = False

    def _store_dir(self) -> Path:
        p = Path(settings.vectorstore_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _load(self):
        if self._loaded:
            return
        d = self._store_dir()
        meta_path    = d / METADATA_FILE
        vectors_path = d / VECTORS_FILE
        try:
            if meta_path.exists() and vectors_path.exists():
                meta = json.loads(meta_path.read_text())
                self._ids       = meta["ids"]
                self._texts     = meta["texts"]
                self._metadatas = meta["metadatas"]
                data = np.load(str(vectors_path))
                self._matrix = data["matrix"]
                logger.info(f"Vector store loaded: {len(self._ids)} vectors, dim={self._matrix.shape[1] if self._matrix.ndim == 2 else 0}")
        except Exception as e:
            logger.warning(f"Vector store load failed (starting fresh): {e}")
            self._ids, self._texts, self._metadatas = [], [], []
            self._matrix = None
        self._loaded = True

    def _save(self):
        d = self._store_dir()
        meta_path    = d / METADATA_FILE
        vectors_path = d / VECTORS_FILE
        try:
            meta_path.write_text(json.dumps({
                "ids":       self._ids,
                "texts":     self._texts,
                "metadatas": self._metadatas,
            }))
            if self._matrix is not None and len(self._matrix) > 0:
                np.savez_compressed(str(vectors_path), matrix=self._matrix)
        except Exception as e:
            logger.error(f"Vector store save failed: {e}")

    # ── Write ──────────────────────────────────────────────────────────────

    def add_embeddings(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        texts: list[str],
        metadatas: list[dict],
    ) -> None:
        self._load()

        new_matrix = np.array(embeddings, dtype=np.float32)

        # Remove any existing entries with the same IDs (upsert)
        existing_set = set(ids)
        keep_mask = [i for i, eid in enumerate(self._ids) if eid not in existing_set]
        if keep_mask:
            self._ids       = [self._ids[i]       for i in keep_mask]
            self._texts     = [self._texts[i]      for i in keep_mask]
            self._metadatas = [self._metadatas[i]  for i in keep_mask]
            self._matrix    = self._matrix[keep_mask] if self._matrix is not None else None

        # Append new entries
        self._ids.extend(ids)
        self._texts.extend(texts)
        self._metadatas.extend(metadatas)

        if self._matrix is None or len(self._matrix) == 0:
            self._matrix = new_matrix
        else:
            # Pad dimensions if vocab grew
            old_dim = self._matrix.shape[1]
            new_dim = new_matrix.shape[1]
            if new_dim > old_dim:
                pad = np.zeros((self._matrix.shape[0], new_dim - old_dim), dtype=np.float32)
                self._matrix = np.hstack([self._matrix, pad])
            elif old_dim > new_dim:
                pad = np.zeros((new_matrix.shape[0], old_dim - new_dim), dtype=np.float32)
                new_matrix = np.hstack([new_matrix, pad])
            self._matrix = np.vstack([self._matrix, new_matrix])

        self._save()
        logger.info(f"Vector store: {len(self._ids)} total vectors stored.")

    # ── Query ──────────────────────────────────────────────────────────────

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 6,
        document_ids: Optional[list[str]] = None,
        min_score: float = 0.0,
    ) -> list[dict]:
        self._load()

        if self._matrix is None or len(self._ids) == 0:
            return []

        q = np.array(query_embedding, dtype=np.float32)

        # Pad query if dimensions differ
        store_dim = self._matrix.shape[1]
        q_dim = len(q)
        if q_dim < store_dim:
            q = np.pad(q, (0, store_dim - q_dim))
        elif q_dim > store_dim:
            q = q[:store_dim]

        # Cosine similarity = dot product (vectors already L2-normalised)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []
        q = q / q_norm

        scores = self._matrix.dot(q)  # shape (N,)

        # Build candidate indices, optionally filtering by document_id
        if document_ids:
            doc_set = set(document_ids)
            candidates = [
                i for i, m in enumerate(self._metadatas)
                if m.get("document_id") in doc_set
            ]
        else:
            candidates = list(range(len(self._ids)))

        if not candidates:
            return []

        candidate_scores = [(i, float(scores[i])) for i in candidates]
        candidate_scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in candidate_scores[:top_k]:
            if score < min_score:
                continue
            m = self._metadatas[idx]
            results.append({
                "chunk_id":      self._ids[idx],
                "document_id":   m.get("document_id", ""),
                "document_name": m.get("document_name", "Unknown"),
                "page_number":   int(m.get("page_number", 0)),
                "section":       m.get("section") or None,
                "text":          self._texts[idx],
                "relevance_score": round(max(0.0, min(1.0, score)), 4),
            })

        return results

    # ── Delete ──────────────────────────────────────────────────────────────

    def delete_document(self, document_id: str) -> int:
        self._load()
        keep = [i for i, m in enumerate(self._metadatas)
                if m.get("document_id") != document_id]
        deleted = len(self._ids) - len(keep)
        if deleted > 0:
            self._ids       = [self._ids[i]       for i in keep]
            self._texts     = [self._texts[i]      for i in keep]
            self._metadatas = [self._metadatas[i]  for i in keep]
            self._matrix    = self._matrix[keep] if self._matrix is not None else None
            self._save()
        logger.info(f"Deleted {deleted} vectors for document {document_id}")
        return deleted

    # ── Stats ───────────────────────────────────────────────────────────────

    def count(self) -> int:
        self._load()
        return len(self._ids)

    def health_check(self) -> dict:
        try:
            return {"status": "ok", "vectors": self.count(), "collection": "numpy_store"}
        except Exception as e:
            return {"status": "error", "error": str(e)}


_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _instance
    if _instance is None:
        _instance = VectorStore()
    return _instance
