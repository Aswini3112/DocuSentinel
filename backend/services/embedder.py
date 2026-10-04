"""
DocuSentinel AI - Embedding Service (Pure NumPy TF-IDF)
No external ML packages required. Uses TF-IDF with numpy for vector generation.
Produces consistent, comparable vectors for similarity search.
"""

import math
import re
import json
import logging
import numpy as np
from pathlib import Path
from typing import Optional
from backend.config import get_settings

logger = logging.getLogger("docusentinel.embedder")
settings = get_settings()

_vocabulary: dict[str, int] = {}
_doc_freq: dict[str, int] = {}
_total_docs: int = 0


def _tokenize(text: str) -> list[str]:
    stopwords = {
        "the","a","an","and","or","but","in","on","at","to","for","of","with",
        "is","are","was","were","be","been","being","have","has","had","do",
        "does","did","will","would","could","should","may","might","shall",
        "this","that","these","those","it","its","as","by","from","than","then",
        "so","if","not","no","nor","yet","both","either","each","all","any",
        "most","other","into","through","during","before","after","above",
        "below","between","out","up","down","per","about","over","under",
    }
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in stopwords and len(t) > 1]


def _get_vocab_path() -> Path:
    p = Path(settings.vectorstore_dir) / "vocab.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_vocab():
    global _vocabulary, _doc_freq, _total_docs
    try:
        vp = _get_vocab_path()
        if vp.exists():
            data = json.loads(vp.read_text())
            _vocabulary = data.get("vocab", {})
            _doc_freq = data.get("doc_freq", {})
            _total_docs = data.get("total_docs", 0)
    except Exception as e:
        logger.warning(f"Could not load vocab: {e}")


def _save_vocab():
    try:
        vp = _get_vocab_path()
        vp.write_text(json.dumps({
            "vocab": _vocabulary,
            "doc_freq": _doc_freq,
            "total_docs": _total_docs,
        }))
    except Exception as e:
        logger.warning(f"Could not save vocab: {e}")


def _update_vocab(texts: list[str]):
    global _vocabulary, _doc_freq, _total_docs
    for text in texts:
        tokens = set(_tokenize(text))
        for t in tokens:
            if t not in _vocabulary:
                _vocabulary[t] = len(_vocabulary)
            _doc_freq[t] = _doc_freq.get(t, 0) + 1
        _total_docs += 1
    _save_vocab()


def _tfidf_vector(text: str, vocab_size: int) -> np.ndarray:
    """Compute a TF-IDF vector for text against the current vocabulary."""
    tokens = _tokenize(text)
    if not tokens:
        return np.zeros(max(vocab_size, 1), dtype=np.float32)

    # Term frequency
    tf: dict[str, float] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    total = len(tokens)
    for t in tf:
        tf[t] = tf[t] / total

    # Build vector
    vec = np.zeros(max(vocab_size, 1), dtype=np.float32)
    n_docs = max(_total_docs, 1)
    for term, count in tf.items():
        idx = _vocabulary.get(term)
        if idx is None or idx >= vocab_size:
            continue
        df = _doc_freq.get(term, 1)
        idf = math.log((n_docs + 1) / (df + 1)) + 1.0
        vec[idx] = count * idf

    # L2 normalize
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate TF-IDF embeddings for a list of texts.
    Updates and persists vocabulary automatically.
    """
    if not texts:
        return []

    _load_vocab()
    _update_vocab(texts)
    vocab_size = len(_vocabulary)

    results = []
    for text in texts:
        vec = _tfidf_vector(text, vocab_size)
        results.append(vec.tolist())

    logger.info(f"Embedded {len(texts)} texts. Vocab size: {vocab_size}")
    return results


def embed_query(query: str) -> list[float]:
    """Embed a single query string using the existing vocabulary."""
    _load_vocab()
    vocab_size = len(_vocabulary)
    if vocab_size == 0:
        logger.warning("Vocabulary is empty — no documents indexed yet.")
        return [0.0] * 128
    vec = _tfidf_vector(query, vocab_size)
    return vec.tolist()
