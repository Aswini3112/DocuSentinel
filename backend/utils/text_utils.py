"""
DocuSentinel AI - Text Utilities
Normalization, cleaning, and claim-extraction helpers.
"""

import re
from datetime import datetime
from typing import Optional


def clean_text(text: str) -> str:
    """Remove excessive whitespace and normalize line endings."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple blank lines into one
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def normalize_date(date_str: str) -> Optional[str]:
    """
    Attempt to parse a date string into ISO format YYYY-MM-DD.
    Returns None if parsing fails.
    """
    formats = [
        "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y",
        "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d",
        "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d",
        "%d %B, %Y", "%B %Y",
    ]
    date_str = date_str.strip()
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def normalize_currency(value_str: str) -> Optional[float]:
    """
    Extract a numeric value from a currency string.
    E.g., '$1,200,000' -> 1200000.0
    """
    cleaned = re.sub(r"[^\d.]", "", value_str.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_dates_from_text(text: str) -> list[str]:
    """
    Find date-like patterns in text and return them as a list of strings.
    """
    # Patterns for common date formats
    patterns = [
        r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b",
        r"\b\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2}\b",
        r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{4}\b",
    ]
    found = []
    for pat in patterns:
        found.extend(re.findall(pat, text, flags=re.IGNORECASE))
    return list(set(found))


def extract_amounts_from_text(text: str) -> list[str]:
    """
    Find monetary amounts or numeric quantities in text.
    """
    patterns = [
        r"\$[\d,]+(?:\.\d{2})?",
        r"USD\s*[\d,]+(?:\.\d{2})?",
        r"EUR\s*[\d,]+(?:\.\d{2})?",
        r"INR\s*[\d,]+(?:\.\d{2})?",
        r"₹\s*[\d,]+(?:\.\d{2})?",
        r"[\d,]+(?:\.\d{2})?\s*(?:USD|EUR|INR|dollars|euros|rupees)",
    ]
    found = []
    for pat in patterns:
        found.extend(re.findall(pat, text, flags=re.IGNORECASE))
    return list(set(found))


def truncate_text(text: str, max_chars: int = 300) -> str:
    """Truncate text to max_chars, appending ellipsis if needed."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "…"
