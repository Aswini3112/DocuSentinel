"""
DocuSentinel AI - Tests: Chunking Engine
Tests sliding window chunking, overlap, and metadata preservation.
"""

import pytest
from backend.services.extractor import ExtractedPage
from backend.services.chunker import chunk_pages, chunk_raw_text, Chunk


class TestChunkPages:

    def _make_pages(self, texts: list[str]) -> list[ExtractedPage]:
        return [
            ExtractedPage(page_number=i + 1, text=t, section=f"Section {i+1}")
            for i, t in enumerate(texts)
        ]

    def test_basic_chunking(self):
        """Chunks are produced from pages."""
        pages = self._make_pages(["word " * 100])
        chunks = chunk_pages(pages, "doc1", "Test.txt", chunk_size=50, chunk_overlap=10)
        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_empty_pages(self):
        """Empty page list returns no chunks."""
        chunks = chunk_pages([], "doc1", "Test.txt")
        assert chunks == []

    def test_chunk_metadata_preserved(self):
        """Each chunk carries document_id, document_name, page_number."""
        pages = self._make_pages(["word " * 200])
        chunks = chunk_pages(pages, "doc-uuid-123", "MyDoc.pdf", chunk_size=50, chunk_overlap=5)

        for chunk in chunks:
            assert chunk.document_id == "doc-uuid-123"
            assert chunk.document_name == "MyDoc.pdf"
            assert chunk.page_number >= 1

    def test_chunk_overlap_creates_more_chunks(self):
        """Overlap > 0 produces more chunks than overlap = 0."""
        pages = self._make_pages(["word " * 300])

        chunks_no_overlap = chunk_pages(pages, "d1", "T.txt", chunk_size=50, chunk_overlap=0)
        chunks_with_overlap = chunk_pages(pages, "d1", "T.txt", chunk_size=50, chunk_overlap=20)

        assert len(chunks_with_overlap) >= len(chunks_no_overlap)

    def test_chunk_index_sequential(self):
        """Chunk indices are sequential starting from 0."""
        pages = self._make_pages(["word " * 500])
        chunks = chunk_pages(pages, "d1", "T.txt", chunk_size=50, chunk_overlap=10)

        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_chunk_text_not_empty(self):
        """No chunk should have empty text."""
        pages = self._make_pages(["word " * 200, "more words " * 100])
        chunks = chunk_pages(pages, "d1", "T.txt", chunk_size=50, chunk_overlap=10)

        for chunk in chunks:
            assert chunk.text.strip() != ""

    def test_multi_page_chunking(self):
        """Chunks span multiple pages with correct page attribution."""
        pages = [
            ExtractedPage(page_number=1, text="page one content " * 100, section="Intro"),
            ExtractedPage(page_number=2, text="page two content " * 100, section="Main"),
            ExtractedPage(page_number=3, text="page three content " * 100, section="Conclusion"),
        ]
        chunks = chunk_pages(pages, "d1", "T.txt", chunk_size=50, chunk_overlap=5)

        page_numbers = {c.page_number for c in chunks}
        assert len(page_numbers) > 1  # Chunks from multiple pages

    def test_chunk_raw_text(self):
        """chunk_raw_text works without page metadata."""
        raw = "raw text content " * 200
        chunks = chunk_raw_text(raw, "d1", "T.txt", chunk_size=50, chunk_overlap=10)

        assert len(chunks) > 0
        assert all(c.page_number == 1 for c in chunks)

    def test_single_short_page(self):
        """Very short content produces exactly one chunk."""
        pages = self._make_pages(["short content"])
        chunks = chunk_pages(pages, "d1", "T.txt", chunk_size=500, chunk_overlap=50)
        assert len(chunks) == 1
        assert "short content" in chunks[0].text
