"""Digitale-PDF-loader — extraheert de tekstlaag (ingest-spec).

PDF's met een tekstlaag worden `pdf_digital` met de geëxtraheerde tekst. PDF's zonder
bruikbare tekstlaag krijgen `pdf_scanned` en lege tekst; OCR is buiten scope voor deze change
(ingest emit het bijbehorende audit-event, niet de loader — die kent de audit-log niet).
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from zeef.ids import content_id
from zeef.models import Document
from zeef.normalize import normalize_text


class PdfLoader:
    """Laadt één PDF naar één `Document` (pdf_digital of pdf_scanned)."""

    def can_load(self, path: Path) -> bool:
        return path.suffix.lower() == ".pdf"

    def load(self, path: Path) -> list[Document]:
        raw = _extract_text(path)
        text = normalize_text(raw)
        doc_type = "pdf_digital" if text else "pdf_scanned"
        meta: dict[str, object] = {"filename": path.name}
        if doc_type == "pdf_scanned":
            meta["ocr"] = "out-of-scope"
        return [Document(
            id=content_id(text, str(path)),
            source_path=str(path),
            doc_type=doc_type,
            metadata=meta,
            text=text,
        )]


def _extract_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)
