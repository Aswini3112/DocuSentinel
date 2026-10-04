"""
DocuSentinel AI - Document Text Extractor
Supports: TXT (stdlib), PDF (PyMuPDF if installed), DOCX (python-docx if installed).
Gracefully degrades to plain-text reading when libraries are absent.
"""

import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger("docusentinel.extractor")


@dataclass
class ExtractedPage:
    page_number: int
    text: str
    section: Optional[str] = None


@dataclass
class ExtractionResult:
    pages: list[ExtractedPage] = field(default_factory=list)
    total_pages: int = 0
    raw_text: str = ""
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and len(self.pages) > 0


def _pages_from_paragraphs(paragraphs: list[str], words_per_page: int = 400) -> list[ExtractedPage]:
    pages: list[ExtractedPage] = []
    page_number = 1
    current: list[str] = []
    wc = 0
    for para in paragraphs:
        current.append(para)
        wc += len(para.split())
        if wc >= words_per_page:
            pages.append(ExtractedPage(page_number=page_number, text="\n\n".join(current)))
            page_number += 1
            current = []
            wc = 0
    if current:
        pages.append(ExtractedPage(page_number=page_number, text="\n\n".join(current)))
    return pages


def extract_txt(file_path: str) -> ExtractionResult:
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if not content.strip():
            return ExtractionResult(error="Text file is empty.")
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        pages = _pages_from_paragraphs(paragraphs)
        raw_text = "\n\n".join(p.text for p in pages)
        return ExtractionResult(pages=pages, total_pages=len(pages), raw_text=raw_text)
    except Exception as e:
        return ExtractionResult(error=f"TXT extraction failed: {e}")


def extract_pdf(file_path: str) -> ExtractionResult:
    try:
        import fitz
        doc = fitz.open(file_path)
        pages: list[ExtractedPage] = []
        for i in range(len(doc)):
            text = doc[i].get_text("text").strip()
            if not text:
                continue
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            section = lines[0] if lines and len(lines[0]) < 80 and not lines[0].endswith(".") else None
            pages.append(ExtractedPage(page_number=i + 1, text=text, section=section))
        doc.close()
        if not pages:
            return ExtractionResult(error="PDF has no extractable text.")
        return ExtractionResult(pages=pages, total_pages=len(pages), raw_text="\n\n".join(p.text for p in pages))
    except ImportError:
        logger.warning("PyMuPDF not installed — trying plain-text fallback for PDF.")
        return extract_txt(file_path)
    except Exception as e:
        return ExtractionResult(error=f"PDF extraction failed: {e}")


def extract_docx(file_path: str) -> ExtractionResult:
    try:
        from docx import Document
        doc = Document(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        if not paragraphs:
            return ExtractionResult(error="DOCX has no readable text.")
        pages = _pages_from_paragraphs(paragraphs)
        return ExtractionResult(pages=pages, total_pages=len(pages), raw_text="\n\n".join(p.text for p in pages))
    except ImportError:
        logger.warning("python-docx not installed — trying plain-text fallback for DOCX.")
        return extract_txt(file_path)
    except Exception as e:
        return ExtractionResult(error=f"DOCX extraction failed: {e}")


def extract_image(file_path: str) -> ExtractionResult:
    try:
        import pytesseract
        from PIL import Image
        text = pytesseract.image_to_string(Image.open(file_path))
        if not text.strip():
            return ExtractionResult(error="OCR produced no readable text.")
        pages = [ExtractedPage(page_number=1, text=text.strip(), section="OCR Extracted")]
        return ExtractionResult(pages=pages, total_pages=1, raw_text=text.strip())
    except ImportError:
        return ExtractionResult(error="pytesseract/Pillow not installed. OCR unavailable.")
    except Exception as e:
        return ExtractionResult(error=f"Image OCR failed: {e}")


def extract_document(file_path: str, file_type: str) -> ExtractionResult:
    dispatch = {"PDF": extract_pdf, "DOCX": extract_docx, "TXT": extract_txt, "IMAGE": extract_image}
    handler = dispatch.get(file_type.upper())
    if handler is None:
        return ExtractionResult(error=f"Unsupported file type: {file_type}")
    logger.info(f"Extracting {file_type}: {file_path}")
    result = handler(file_path)
    if result.success:
        logger.info(f"Extraction OK: {result.total_pages} pages, {len(result.raw_text)} chars")
    else:
        logger.warning(f"Extraction issue: {result.error}")
    return result
