"""
DocuSentinel AI - Tests: API Endpoints
Integration tests for all FastAPI routes.
Uses the test client with in-memory DB and mocked services.
"""

import io
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


# ─────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────

class TestHealthEndpoint:

    @pytest.mark.asyncio
    async def test_health_ok(self, client):
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "app" in data
        assert data["app"] == "DocuSentinel AI"

    @pytest.mark.asyncio
    async def test_root_returns_tagline(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "DocuSentinel AI" in data["app"]
        assert "tagline" in data

    @pytest.mark.asyncio
    async def test_stats_endpoint(self, client):
        response = await client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "documents_analyzed" in data
        assert "conflicts_detected" in data
        assert "evidence_coverage" in data


# ─────────────────────────────────────────────
# Document Upload
# ─────────────────────────────────────────────

class TestDocumentUpload:

    @pytest.mark.asyncio
    async def test_upload_unsupported_type(self, client):
        """Unsupported file type returns 415."""
        file_content = io.BytesIO(b"test content")
        response = await client.post(
            "/api/documents/upload",
            files={"file": ("malware.exe", file_content, "application/octet-stream")},
        )
        assert response.status_code == 415

    @pytest.mark.asyncio
    async def test_upload_empty_file(self, client):
        """Empty file returns 400."""
        file_content = io.BytesIO(b"")
        response = await client.post(
            "/api/documents/upload",
            files={"file": ("empty.txt", file_content, "text/plain")},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_valid_txt(self, client, sample_txt_content, tmp_path):
        """Valid TXT file upload returns 202 with document record."""
        with patch("backend.routes.documents.settings") as mock_settings:
            mock_settings.max_file_size_bytes = 10 * 1024 * 1024
            mock_settings.upload_path = tmp_path
            mock_settings.chunk_size = 500
            mock_settings.chunk_overlap = 50

            file_content = io.BytesIO(sample_txt_content)
            response = await client.post(
                "/api/documents/upload",
                files={"file": ("test_contract.txt", file_content, "text/plain")},
            )

        assert response.status_code in (200, 202)
        data = response.json()
        assert "id" in data
        assert data["original_name"] == "test_contract.txt"
        assert data["status"] in ("uploading", "extracting", "indexing", "ready")

    @pytest.mark.asyncio
    async def test_list_documents(self, client):
        """Document list endpoint returns list structure."""
        response = await client.get("/api/documents")
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "total" in data
        assert isinstance(data["documents"], list)

    @pytest.mark.asyncio
    async def test_get_nonexistent_document(self, client):
        """Getting a non-existent document returns 404."""
        response = await client.get("/api/documents/nonexistent-uuid-1234")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(self, client):
        """Deleting a non-existent document returns 404."""
        response = await client.delete("/api/documents/nonexistent-uuid-1234")
        assert response.status_code == 404


# ─────────────────────────────────────────────
# Investigation
# ─────────────────────────────────────────────

class TestInvestigateEndpoint:

    @pytest.mark.asyncio
    async def test_empty_question_rejected(self, client):
        """Empty question returns 400 or 422."""
        response = await client.post(
            "/api/investigate",
            json={"question": "  "},
        )
        assert response.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_investigate_no_documents(self, client):
        """Investigation with no documents returns NOT_FOUND status."""
        from backend.models.schemas import EvidenceItem, InlineConflict, SourceReference
        from backend.services.investigator import run_investigation

        mock_response = MagicMock()
        mock_response.id = "test-inv-001"
        mock_response.question = "What is the deadline?"
        mock_response.answer = "No relevant evidence found."
        mock_response.answer_status = "NOT_FOUND"
        mock_response.confidence_score = 0.0
        mock_response.confidence_percent = 0
        mock_response.confidence_reason = "No evidence retrieved."
        mock_response.evidence_strength = "None"
        mock_response.has_conflict = False
        mock_response.evidence = []
        mock_response.sources = []
        mock_response.conflicts = []
        mock_response.llm_used = False
        mock_response.llm_status = "NOT_CONFIGURED"
        mock_response.llm_status_msg = "No key configured."
        from datetime import datetime
        mock_response.created_at = datetime.utcnow()

        with patch(
            "backend.routes.investigate.run_investigation",
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            response = await client.post(
                "/api/investigate",
                json={"question": "What is the project deadline?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["answer_status"] == "NOT_FOUND"
        assert data["confidence_percent"] == 0

    @pytest.mark.asyncio
    async def test_investigations_list(self, client):
        """Investigations list returns correct structure."""
        response = await client.get("/api/investigations")
        assert response.status_code == 200
        data = response.json()
        assert "investigations" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_investigation_not_found(self, client):
        """Non-existent investigation returns 404."""
        response = await client.get("/api/investigations/nonexistent-uuid")
        assert response.status_code == 404


# ─────────────────────────────────────────────
# Conflicts
# ─────────────────────────────────────────────

class TestConflictsEndpoint:

    @pytest.mark.asyncio
    async def test_list_conflicts_empty(self, client):
        """Empty conflict list returns valid structure."""
        response = await client.get("/api/conflicts")
        assert response.status_code == 200
        data = response.json()
        assert "conflicts" in data
        assert "total" in data
        assert "high" in data
        assert "medium" in data
        assert "low" in data

    @pytest.mark.asyncio
    async def test_conflict_not_found(self, client):
        """Non-existent conflict returns 404."""
        response = await client.get("/api/conflicts/nonexistent-uuid")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_conflicts_invalid_severity(self, client):
        """Invalid severity filter returns 400."""
        response = await client.get("/api/conflicts?severity=INVALID")
        assert response.status_code == 400


# ─────────────────────────────────────────────
# Evidence
# ─────────────────────────────────────────────

class TestEvidenceEndpoint:

    @pytest.mark.asyncio
    async def test_evidence_chunk_not_found(self, client):
        """Non-existent chunk returns 404."""
        response = await client.get("/api/evidence/nonexistent-chunk-id")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_evidence_graph_returns_structure(self, client):
        """Graph data endpoint returns nodes/edges structure."""
        response = await client.get("/api/evidence/graph/data")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "summary" in data

    @pytest.mark.asyncio
    async def test_document_chunks_not_found(self, client):
        """Chunks for non-existent document returns 404."""
        response = await client.get("/api/evidence/document/nonexistent-doc-id")
        assert response.status_code == 404
