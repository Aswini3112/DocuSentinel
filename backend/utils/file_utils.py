"""
DocuSentinel AI - File Utilities
Handles file validation, safe naming, and temporary file operations.
"""

import os
import uuid
import hashlib
from pathlib import Path
from typing import Optional

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/bmp",
}


def validate_file_extension(filename: str) -> bool:
    """Check if the file extension is allowed."""
    suffix = Path(filename).suffix.lower()
    return suffix in ALLOWED_EXTENSIONS


def get_file_type(filename: str) -> str:
    """Return a normalized file type string."""
    suffix = Path(filename).suffix.lower()
    type_map = {
        ".pdf": "PDF",
        ".docx": "DOCX",
        ".txt": "TXT",
        ".png": "IMAGE",
        ".jpg": "IMAGE",
        ".jpeg": "IMAGE",
        ".tiff": "IMAGE",
        ".bmp": "IMAGE",
    }
    return type_map.get(suffix, "UNKNOWN")


def safe_filename(original_name: str) -> str:
    """Generate a safe unique filename while preserving the original extension."""
    ext = Path(original_name).suffix.lower()
    unique_id = uuid.uuid4().hex
    return f"{unique_id}{ext}"


def compute_file_hash(file_bytes: bytes) -> str:
    """Compute SHA-256 hash of file content for deduplication."""
    return hashlib.sha256(file_bytes).hexdigest()


def human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024**2):.1f} MB"
    return f"{size_bytes / (1024**3):.1f} GB"
