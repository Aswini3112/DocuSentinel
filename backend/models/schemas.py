"""
DocuSentinel AI - Pydantic Schemas
Request/response models for all API endpoints.
"""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Document Schemas
# ─────────────────────────────────────────────

class DocumentBase(BaseModel):
    original_name: str
    file_type: str
    file_size: int


class DocumentResponse(BaseModel):
    id: str
    original_name: str
    file_type: str
    file_size: int
    status: str
    page_count: int
    chunk_count: int
    is_demo: bool
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class DocumentDetailResponse(DocumentResponse):
    """Extended response including sample chunks."""
    sample_chunks: list[dict] = []


# ─────────────────────────────────────────────
# Chunk Schemas
# ─────────────────────────────────────────────

class ChunkResponse(BaseModel):
    id: str
    document_id: str
    document_name: str
    chunk_index: int
    text: str
    page_number: int
    section: Optional[str] = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Evidence Schemas
# ─────────────────────────────────────────────

class EvidenceItem(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    section: Optional[str] = None
    text: str
    relevance_score: float = Field(ge=0.0, le=1.0)


# ─────────────────────────────────────────────
# Source Reference Schemas
# ─────────────────────────────────────────────

class SourceReference(BaseModel):
    document_id: str
    document_name: str
    page_number: int
    section: Optional[str] = None
    excerpt: str


# ─────────────────────────────────────────────
# Conflict Schemas
# ─────────────────────────────────────────────

class ConflictResponse(BaseModel):
    id: str
    field: str
    document_a_name: str
    document_b_name: str
    document_a_id: str
    document_b_id: str
    value_a: str
    value_b: str
    severity: str
    status: str
    description: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConflictListResponse(BaseModel):
    conflicts: list[ConflictResponse]
    total: int
    high: int
    medium: int
    low: int


class InlineConflict(BaseModel):
    """Conflict detected inline during an investigation."""
    field: str
    value_a: str
    source_a: str
    page_a: int
    value_b: str
    source_b: str
    page_b: int
    severity: str


# ─────────────────────────────────────────────
# Investigation Schemas
# ─────────────────────────────────────────────

class InvestigateRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    document_ids: Optional[list[str]] = None  # None = search all documents


class InvestigateResponse(BaseModel):
    id: str
    question: str
    answer: str
    answer_status: str        # VERIFIED | CONFLICTING | UNCERTAIN | NOT_FOUND
    confidence_score: float   # 0.0 – 1.0
    confidence_percent: int   # rounded percentage for display
    confidence_reason: str
    evidence_strength: str    # "High" | "Medium" | "Low" | "None"
    has_conflict: bool
    evidence: list[EvidenceItem]
    sources: list[SourceReference]
    conflicts: list[InlineConflict]
    # LLM provider status — always honest
    llm_used: bool = False
    llm_status: str = "NOT_CONFIGURED"   # CONFIGURED | NOT_CONFIGURED | ERROR
    llm_status_msg: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}


class InvestigationListItem(BaseModel):
    id: str
    question: str
    answer_status: str
    confidence_score: float
    has_conflict: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class InvestigationListResponse(BaseModel):
    investigations: list[InvestigationListItem]
    total: int


# ─────────────────────────────────────────────
# Claim Schemas
# ─────────────────────────────────────────────

class ClaimResponse(BaseModel):
    id: str
    document_id: str
    document_name: str
    field: str
    raw_value: str
    normalized_value: Optional[str] = None
    page_number: int
    context_text: Optional[str] = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Dashboard / Stats Schemas
# ─────────────────────────────────────────────

class DashboardStats(BaseModel):
    documents_analyzed: int
    claims_extracted: int
    conflicts_detected: int
    uncertain_claims: int
    evidence_coverage: float  # 0–100
    answer_confidence: float  # 0–100 (average)
    conflict_risk: float      # 0–100


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    database: str
    vector_store: str
    llm: str
    llm_status: str = "NOT_CONFIGURED"   # CONFIGURED | NOT_CONFIGURED | ERROR
    llm_model: Optional[str] = None
    llm_message: str = ""


# ─────────────────────────────────────────────
# Error Schema
# ─────────────────────────────────────────────

class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
