"""
DocuSentinel AI - Conflict Detection Engine
The core differentiator: detects when documents disagree on factual claims.

Two detection strategies:
1. DB-level claim comparison  — runs after ingestion, compares normalized claims
2. Evidence-level comparison  — runs at query time, detects conflicts in retrieved chunks
"""

import re
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from backend.models.db_models import Claim, Conflict, Document, ConflictSeverity, ConflictStatus
from backend.models.schemas import EvidenceItem, InlineConflict

logger = logging.getLogger("docusentinel.conflict")


# ─────────────────────────────────────────────
# Severity Rules
# ─────────────────────────────────────────────

FIELD_SEVERITY = {
    "deadline":       ConflictSeverity.HIGH,
    "start_date":     ConflictSeverity.HIGH,
    "payment_amount": ConflictSeverity.HIGH,
    "project_owner":  ConflictSeverity.MEDIUM,
    "penalty":        ConflictSeverity.HIGH,
    "duration":       ConflictSeverity.MEDIUM,
    "version":        ConflictSeverity.LOW,
}


# ─────────────────────────────────────────────
# Post-Ingestion: DB Claim Comparison
# ─────────────────────────────────────────────

async def detect_conflicts_for_document(
    new_document_id: str,
    db: AsyncSession,
) -> list[Conflict]:
    """
    After a new document is ingested, compare its claims against all
    existing claims from OTHER documents.
    Saves new Conflict records to the DB and returns them.
    """
    # Load new document's claims
    new_claims_result = await db.execute(
        select(Claim).where(Claim.document_id == new_document_id)
    )
    new_claims = new_claims_result.scalars().all()

    if not new_claims:
        return []

    # Load all claims from other documents
    other_claims_result = await db.execute(
        select(Claim).where(Claim.document_id != new_document_id)
    )
    other_claims = other_claims_result.scalars().all()

    if not other_claims:
        return []

    new_conflicts: list[Conflict] = []

    for new_claim in new_claims:
        for other_claim in other_claims:
            # Must be same field to compare
            if new_claim.field != other_claim.field:
                continue

            # Must be from different documents
            if new_claim.document_id == other_claim.document_id:
                continue

            # Check for value disagreement
            if not _values_conflict(new_claim, other_claim):
                continue

            # Check for existing conflict record to avoid duplicates
            existing = await db.execute(
                select(Conflict).where(
                    and_(
                        Conflict.field == new_claim.field,
                        Conflict.document_a_id == new_claim.document_id,
                        Conflict.document_b_id == other_claim.document_id,
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue

            severity = FIELD_SEVERITY.get(new_claim.field, ConflictSeverity.LOW)

            conflict = Conflict(
                field=new_claim.field,
                claim_a_id=new_claim.id,
                claim_b_id=other_claim.id,
                document_a_id=new_claim.document_id,
                document_b_id=other_claim.document_id,
                value_a=new_claim.raw_value,
                value_b=other_claim.raw_value,
                severity=severity,
                status=ConflictStatus.OPEN,
                description=_build_conflict_description(new_claim, other_claim),
            )
            db.add(conflict)
            new_conflicts.append(conflict)

    if new_conflicts:
        await db.commit()
        logger.info(f"Detected {len(new_conflicts)} new conflicts for document {new_document_id}")

    return new_conflicts


def _values_conflict(claim_a: Claim, claim_b: Claim) -> bool:
    """
    Determine if two claim values represent a genuine contradiction.
    Uses normalized values where available, raw values otherwise.
    """
    val_a = (claim_a.normalized_value or claim_a.raw_value).strip().lower()
    val_b = (claim_b.normalized_value or claim_b.raw_value).strip().lower()

    if not val_a or not val_b:
        return False

    # Exact match = no conflict
    if val_a == val_b:
        return False

    # For numeric fields (amounts), allow small tolerance (< 1%)
    if claim_a.field == "payment_amount":
        try:
            a_num = float(re.sub(r"[^\d.]", "", val_a))
            b_num = float(re.sub(r"[^\d.]", "", val_b))
            if a_num == 0:
                return b_num != 0
            ratio = abs(a_num - b_num) / a_num
            return ratio > 0.01  # > 1% difference = conflict
        except (ValueError, ZeroDivisionError):
            pass

    # For text fields, minor whitespace/case differences are not conflicts
    if _normalize_for_comparison(val_a) == _normalize_for_comparison(val_b):
        return False

    return True


def _normalize_for_comparison(text: str) -> str:
    """Strip extra whitespace and punctuation for fuzzy comparison."""
    return re.sub(r"[^\w]", "", text.lower())


def _build_conflict_description(claim_a: Claim, claim_b: Claim) -> str:
    return (
        f"Conflicting values for '{claim_a.field}': "
        f"Document A states '{claim_a.raw_value}' "
        f"while Document B states '{claim_b.raw_value}'."
    )


# ─────────────────────────────────────────────
# Query-Time: Evidence-Level Conflict Detection
# ─────────────────────────────────────────────

def detect_inline_conflicts(evidence: list[EvidenceItem]) -> list[InlineConflict]:
    """
    Scan retrieved evidence chunks for contradictory factual claims.
    Runs at query time — does not require pre-computed claim records.
    Catches conflicts that pattern-based extraction might miss.

    Strategy:
    - Extract key facts (dates, numbers, names) from each evidence chunk.
    - Compare same-typed facts across different documents.
    - Flag pairs that disagree.
    """
    if len(evidence) < 2:
        return []

    inline_conflicts: list[InlineConflict] = []

    # Group evidence by document
    doc_evidence: dict[str, list[EvidenceItem]] = {}
    for item in evidence:
        doc_evidence.setdefault(item.document_id, []).append(item)

    if len(doc_evidence) < 2:
        return []  # All evidence from same document — no cross-doc conflict possible

    # Extract facts from each document's evidence
    doc_facts: dict[str, dict] = {}
    for doc_id, items in doc_evidence.items():
        combined_text = " ".join(i.text for i in items)
        doc_name = items[0].document_name
        page = items[0].page_number
        doc_facts[doc_id] = {
            "name": doc_name,
            "page": page,
            "facts": _extract_inline_facts(combined_text),
        }

    # Compare facts across document pairs
    doc_ids = list(doc_facts.keys())
    for i in range(len(doc_ids)):
        for j in range(i + 1, len(doc_ids)):
            id_a = doc_ids[i]
            id_b = doc_ids[j]
            facts_a = doc_facts[id_a]["facts"]
            facts_b = doc_facts[id_b]["facts"]

            for field, values_a in facts_a.items():
                values_b = facts_b.get(field, [])
                if not values_b:
                    continue

                # Check if any value pairs conflict
                for val_a in values_a:
                    for val_b in values_b:
                        norm_a = _normalize_for_comparison(val_a)
                        norm_b = _normalize_for_comparison(val_b)
                        if norm_a and norm_b and norm_a != norm_b:
                            severity = _inline_severity(field)
                            inline_conflicts.append(InlineConflict(
                                field=field,
                                value_a=val_a,
                                source_a=doc_facts[id_a]["name"],
                                page_a=doc_facts[id_a]["page"],
                                value_b=val_b,
                                source_b=doc_facts[id_b]["name"],
                                page_b=doc_facts[id_b]["page"],
                                severity=severity,
                            ))

    # Deduplicate conflicts by field+value pair
    seen = set()
    unique_conflicts = []
    for c in inline_conflicts:
        key = (c.field, _normalize_for_comparison(c.value_a), _normalize_for_comparison(c.value_b))
        if key not in seen:
            seen.add(key)
            unique_conflicts.append(c)

    logger.info(f"Inline conflict detection found {len(unique_conflicts)} conflicts")
    return unique_conflicts


def _extract_inline_facts(text: str) -> dict[str, list[str]]:
    """
    Extract key factual values from a text chunk for inline comparison.
    Returns dict: {field_name: [value1, value2, ...]}
    """
    facts: dict[str, list[str]] = {}

    patterns = {
        "deadline": [
            # matches "deadline: date", "deadline is date", "deadline of date"
            r"(?:deadline|due date|delivery date|end date|target date|completion date)"
            r"\s*(?:is|are|was|will be|:|\-|–|by|of|on)?\s*"
            r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}"
            r"|\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}"
            r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s+\d{1,2},?\s+\d{4})",
        ],
        "payment_amount": [
            r"(?:total|amount|cost|budget|payment|fee|price|contract value)"
            r"\s*(?:is|are|was|of|:|\-|–)?\s*"
            r"((?:USD|EUR|INR|\$|€|₹)\s*[\d,]+(?:\.\d{2})?)",
        ],
        "project_owner": [
            r"(?:project manager|owner|responsible|client|vendor)\s*(?:is|:|\-|–)?\s*"
            r"([A-Z][a-zA-Z\s]{2,40}(?:Ltd|LLC|Inc|Corp)?\.?)",
        ],
        "duration": [
            r"(?:duration|period|term)\s*(?:is|:|\-|–)?\s*(\d+\s*(?:days?|weeks?|months?|years?))",
        ],
        "penalty": [
            r"(?:penalty|fine|liquidated damages)\s*(?:is|of|:|\-|–)?\s*"
            r"((?:USD|EUR|INR|\$|€|₹)\s*[\d,]+(?:\.\d{2})?|\d+(?:\.\d+)?%)",
        ],
    }

    for field, field_patterns in patterns.items():
        found = []
        for pat in field_patterns:
            matches = re.findall(pat, text, flags=re.IGNORECASE)
            found.extend(matches)
        if found:
            facts[field] = list(set(m.strip() for m in found if m.strip()))

    return facts


def _inline_severity(field: str) -> str:
    severity_map = {
        "deadline":       "HIGH",
        "payment_amount": "HIGH",
        "penalty":        "HIGH",
        "project_owner":  "MEDIUM",
        "duration":       "MEDIUM",
    }
    return severity_map.get(field, "LOW")


def build_conflict_summary(conflicts: list[InlineConflict]) -> str:
    """Build a plain-text summary of detected conflicts for the LLM prompt."""
    if not conflicts:
        return ""
    lines = []
    for c in conflicts:
        lines.append(
            f"• {c.field.upper()}: "
            f"'{c.source_a}' (p.{c.page_a}) states '{c.value_a}' "
            f"vs '{c.source_b}' (p.{c.page_b}) states '{c.value_b}'"
        )
    return "\n".join(lines)
