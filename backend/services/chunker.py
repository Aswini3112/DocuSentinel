"""
DocuSentinel AI - Document Chunker
Splits extracted pages into overlapping chunks for embedding.
Strategy: sentence-aware sliding window — never cuts mid-sentence.
Preserves full source metadata: document_id, document_name, page_number, section.
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional
from backend.services.extractor import ExtractedPage
from backend.utils.text_utils import clean_text

logger = logging.getLogger("docusentinel.chunker")


@dataclass
class Chunk:
    """A single chunk of text with full source provenance."""
    document_id: str
    document_name: str
    chunk_index: int
    text: str
    page_number: int
    section: Optional[str]
    char_start: int
    char_end: int


def _split_sentences(text: str) -> list[str]:
    """
    Split text into sentences using punctuation boundaries.
    Keeps each sentence intact so chunks never cut mid-sentence.
    """
    # Split on sentence-ending punctuation followed by space/newline
    raw = re.split(r'(?<=[.!?])\s+', text.strip())
    # Also split on newlines that look like list items or headings
    sentences = []
    for part in raw:
        sub = re.split(r'\n{2,}', part)
        sentences.extend(s.strip() for s in sub if s.strip())
    return sentences


def chunk_pages(
    pages: list[ExtractedPage],
    document_id: str,
    document_name: str,
    chunk_size: int = 150,
    chunk_overlap: int = 20,
) -> list[Chunk]:
    """
    Sentence-aware sliding window chunker.

    1. Split each page's text into sentences.
    2. Accumulate sentences until word count reaches chunk_size.
    3. Overlap: retain the last `chunk_overlap` words from the previous chunk
       as the start of the next (keeps context across chunk boundaries).
    4. Every chunk records its dominant page_number and section.
    """
    if not pages:
        return []

    # Build a flat sentence list with page/section metadata
    # Each entry: (sentence_text, page_number, section)
    sentence_meta: list[tuple[str, int, Optional[str]]] = []
    for page in pages:
        cleaned = clean_text(page.text)
        for sent in _split_sentences(cleaned):
            if sent.strip():
                sentence_meta.append((sent, page.page_number, page.section))

    if not sentence_meta:
        return []

    chunks: list[Chunk] = []
    chunk_index = 0
    sent_idx = 0
    overlap_prefix: list[str] = []   # words carried from previous chunk
    char_cursor = 0

    while sent_idx < len(sentence_meta):
        current_sentences: list[str] = []
        current_pages: dict[int, int] = {}
        current_sections: dict[Optional[str], int] = {}
        word_count = 0

        # Start with overlap prefix from previous chunk
        if overlap_prefix:
            seed = " ".join(overlap_prefix)
            current_sentences.append(seed)
            word_count += len(overlap_prefix)

        # Accumulate sentences until we hit chunk_size
        start_sent_idx = sent_idx
        while sent_idx < len(sentence_meta):
            sent, pn, sec = sentence_meta[sent_idx]
            sent_words = len(sent.split())

            # Always take at least one sentence per chunk
            if word_count + sent_words > chunk_size and current_sentences and word_count > 0:
                break

            current_sentences.append(sent)
            word_count += sent_words
            current_pages[pn] = current_pages.get(pn, 0) + sent_words
            current_sections[sec] = current_sections.get(sec, 0) + sent_words
            sent_idx += 1

        # Build chunk text
        chunk_text = " ".join(current_sentences).strip()
        if not chunk_text:
            continue

        dominant_page = max(current_pages, key=current_pages.get) if current_pages else 1
        dominant_section = max(current_sections, key=current_sections.get) if current_sections else None

        chunks.append(Chunk(
            document_id=document_id,
            document_name=document_name,
            chunk_index=chunk_index,
            text=chunk_text,
            page_number=dominant_page,
            section=dominant_section,
            char_start=char_cursor,
            char_end=char_cursor + len(chunk_text),
        ))
        char_cursor += len(chunk_text) + 1
        chunk_index += 1

        # Compute overlap: last chunk_overlap words of this chunk
        all_words = chunk_text.split()
        overlap_prefix = all_words[-chunk_overlap:] if len(all_words) > chunk_overlap else []

    # Safety: if nothing was produced, fall back to one big chunk
    if not chunks:
        all_text = " ".join(s for s, _, _ in sentence_meta)
        chunks.append(Chunk(
            document_id=document_id,
            document_name=document_name,
            chunk_index=0,
            text=all_text[:3000],
            page_number=sentence_meta[0][1],
            section=sentence_meta[0][2],
            char_start=0,
            char_end=len(all_text[:3000]),
        ))

    logger.info(
        f"Chunking: '{document_name}' "
        f"{len(pages)} pages → {len(chunks)} chunks "
        f"(size≤{chunk_size}w, overlap={chunk_overlap}w)"
    )
    return chunks


def chunk_raw_text(
    raw_text: str,
    document_id: str,
    document_name: str,
    chunk_size: int = 150,
    chunk_overlap: int = 20,
) -> list[Chunk]:
    """Convenience wrapper: treat raw text as a single page."""
    page = ExtractedPage(page_number=1, text=raw_text, section=None)
    return chunk_pages(
        pages=[page],
        document_id=document_id,
        document_name=document_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
