"""
DocuSentinel AI - Claim Extractor
Identifies and normalizes factual claims (dates, amounts, names, deadlines, etc.)
from document chunks using regex patterns.
These claims power the conflict detection engine.
"""

import re
import logging
from typing import Optional
from backend.services.chunker import Chunk
from backend.utils.text_utils import normalize_date, normalize_currency, extract_dates_from_text

logger = logging.getLogger("docusentinel.claim_extractor")


# ─────────────────────────────────────────────
# Claim Pattern Definitions
# ─────────────────────────────────────────────

# Each pattern: (field_name, regex, value_group_index)
CLAIM_PATTERNS = [
    # Deadlines / Due dates — matches "deadline: date", "deadline is date", "by date"
    (
        "deadline",
        r"(?:deadline|due date|completion date|delivery date|end date|target date|must.*complet|shall.*deliver)"
        r"\s*(?:is|are|was|will be|:|\-|–|by|on)?\s*"
        r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}"
        r"|\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}"
        r"|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}"
        r"|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{4})",
        1,
    ),
    # Contract / project start date
    (
        "start_date",
        r"(?:start date|commencement date|effective date|project start)"
        r"\s*(?:is|are|:|\-|–)?\s*"
        r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}"
        r"|\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}"
        r"|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})",
        1,
    ),
    # Payment amounts — matches "total contract value is USD X", "total amount: $X"
    (
        "payment_amount",
        r"(?:payment|total amount|contract value|project cost|budget|fee|price|sum|total)"
        r"\s*(?:is|are|was|:|\-|–|of)?\s*"
        r"((?:USD|EUR|INR|GBP|\$|€|£|₹)\s*[\d,]+(?:\.\d{2})?|[\d,]+(?:\.\d{2})?\s*(?:USD|EUR|INR|GBP|dollars|euros|rupees))",
        1,
    ),
    # Project owner / responsible party
    (
        "project_owner",
        r"(?:project owner|project manager|responsible party|client|vendor|contractor|party)\s*[:\-–]?\s*"
        r"([A-Z][a-zA-Z\s&.,]{2,60}(?:Ltd|LLC|Inc|Corp|Limited|Pvt)?\.?)",
        1,
    ),
    # Penalty / late fee
    (
        "penalty",
        r"(?:penalty|late fee|liquidated damages|fine)\s*[:\-–]?\s*"
        r"((?:USD|EUR|INR|\$|€|₹)\s*[\d,]+(?:\.\d{2})?|[\d,]+(?:\.\d{2})?\s*(?:USD|EUR|INR)|\d+(?:\.\d+)?%)",
        1,
    ),
    # Duration
    (
        "duration",
        r"(?:duration|project duration|contract period|term)\s*[:\-–]?\s*"
        r"(\d+\s*(?:days?|weeks?|months?|years?))",
        1,
    ),
    # Version / revision
    (
        "version",
        r"(?:version|revision|rev\.?)\s*[:\-–]?\s*"
        r"(v?[\d]+(?:\.[\d]+)*(?:\s*[a-zA-Z]+)?)",
        1,
    ),
]


def extract_claims_from_chunks(
    chunks: list[Chunk],
    document_id: str,
) -> list[dict]:
    """
    Scan all chunks for factual claims using pattern matching.
    Returns a list of claim dicts ready for DB insertion.
    """
    found_claims: list[dict] = []

    for chunk in chunks:
        text = chunk.text
        text_lower = text.lower()

        for field_name, pattern, value_group in CLAIM_PATTERNS:
            try:
                matches = re.finditer(pattern, text, flags=re.IGNORECASE)
                for match in matches:
                    raw_value = match.group(value_group).strip()
                    if not raw_value or len(raw_value) < 2:
                        continue

                    # Normalize the value
                    normalized = _normalize_value(field_name, raw_value)

                    # Avoid duplicates within same document
                    is_duplicate = any(
                        c["field"] == field_name
                        and c["normalized_value"] == normalized
                        and c["document_id"] == document_id
                        for c in found_claims
                    )
                    if is_duplicate:
                        continue

                    # Extract a short context window around the match
                    start = max(0, match.start() - 80)
                    end = min(len(text), match.end() + 80)
                    context = text[start:end].strip()

                    found_claims.append({
                        "document_id":      document_id,
                        "chunk_index":      chunk.chunk_index,
                        "field":            field_name,
                        "raw_value":        raw_value,
                        "normalized_value": normalized,
                        "page_number":      chunk.page_number,
                        "context_text":     context,
                    })

            except re.error as re_err:
                logger.warning(f"Regex error for field '{field_name}': {re_err}")

    logger.debug(f"Extracted {len(found_claims)} claims from {len(chunks)} chunks")
    return found_claims


def _normalize_value(field: str, raw_value: str) -> Optional[str]:
    """Normalize a claim value based on its field type."""
    if field in ("deadline", "start_date"):
        normalized = normalize_date(raw_value)
        return normalized if normalized else raw_value

    if field == "payment_amount":
        amount = normalize_currency(raw_value)
        return f"{amount:.2f}" if amount is not None else raw_value

    return raw_value.strip()
