"""
DocuSentinel AI - SQLAlchemy ORM Models
Defines all database tables for documents, chunks, investigations, conflicts, and claims.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base

import enum


def new_uuid() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.utcnow()


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class DocumentStatus(str, enum.Enum):
    UPLOADING   = "uploading"
    EXTRACTING  = "extracting"
    INDEXING    = "indexing"
    READY       = "ready"
    FAILED      = "failed"


class DocumentType(str, enum.Enum):
    PDF     = "PDF"
    DOCX    = "DOCX"
    TXT     = "TXT"
    IMAGE   = "IMAGE"
    UNKNOWN = "UNKNOWN"


class ConflictSeverity(str, enum.Enum):
    HIGH   = "HIGH"
    MEDIUM = "MEDIUM"
    LOW    = "LOW"


class ConflictStatus(str, enum.Enum):
    OPEN     = "open"
    RESOLVED = "resolved"
    IGNORED  = "ignored"


class AnswerStatus(str, enum.Enum):
    VERIFIED    = "VERIFIED"
    CONFLICTING = "CONFLICTING"
    UNCERTAIN   = "UNCERTAIN"
    NOT_FOUND   = "NOT_FOUND"


# ─────────────────────────────────────────────
# Document
# ─────────────────────────────────────────────

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    original_name: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(SAEnum(DocumentType), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(SAEnum(DocumentStatus), default=DocumentStatus.UPLOADING)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)

    # Relationships
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )
    claims: Mapped[list["Claim"]] = relationship(
        "Claim", back_populates="document", cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────
# Document Chunk
# ─────────────────────────────────────────────

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, default=0)
    section: Mapped[str] = mapped_column(String(500), nullable=True)
    char_start: Mapped[int] = mapped_column(Integer, default=0)
    char_end: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    # Relationship
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")


# ─────────────────────────────────────────────
# Claim (extracted factual assertion)
# ─────────────────────────────────────────────

class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    chunk_id: Mapped[str] = mapped_column(ForeignKey("document_chunks.id"), nullable=True)
    field: Mapped[str] = mapped_column(String(200), nullable=False)   # e.g. "deadline"
    raw_value: Mapped[str] = mapped_column(String(500), nullable=False)  # e.g. "15 November 2026"
    normalized_value: Mapped[str] = mapped_column(String(200), nullable=True)  # e.g. "2026-11-15"
    page_number: Mapped[int] = mapped_column(Integer, default=0)
    context_text: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    # Relationship
    document: Mapped["Document"] = relationship("Document", back_populates="claims")


# ─────────────────────────────────────────────
# Conflict
# ─────────────────────────────────────────────

class Conflict(Base):
    __tablename__ = "conflicts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    field: Mapped[str] = mapped_column(String(200), nullable=False)
    claim_a_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), nullable=False)
    claim_b_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), nullable=False)
    document_a_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    document_b_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    value_a: Mapped[str] = mapped_column(String(500), nullable=False)
    value_b: Mapped[str] = mapped_column(String(500), nullable=False)
    severity: Mapped[str] = mapped_column(SAEnum(ConflictSeverity), default=ConflictSeverity.MEDIUM)
    status: Mapped[str] = mapped_column(SAEnum(ConflictStatus), default=ConflictStatus.OPEN)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    # Relationships (load document names for display)
    document_a: Mapped["Document"] = relationship("Document", foreign_keys=[document_a_id])
    document_b: Mapped["Document"] = relationship("Document", foreign_keys=[document_b_id])
    claim_a: Mapped["Claim"] = relationship("Claim", foreign_keys=[claim_a_id])
    claim_b: Mapped["Claim"] = relationship("Claim", foreign_keys=[claim_b_id])


# ─────────────────────────────────────────────
# Investigation (a Q&A session entry)
# ─────────────────────────────────────────────

class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=True)
    answer_status: Mapped[str] = mapped_column(SAEnum(AnswerStatus), default=AnswerStatus.UNCERTAIN)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_reason: Mapped[str] = mapped_column(Text, nullable=True)
    evidence_strength: Mapped[str] = mapped_column(String(50), nullable=True)  # "High" | "Medium" | "Low"
    has_conflict: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=True)   # JSON list of evidence chunks
    sources_json: Mapped[str] = mapped_column(Text, nullable=True)    # JSON list of source refs
    conflicts_json: Mapped[str] = mapped_column(Text, nullable=True)  # JSON list of detected conflicts
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
