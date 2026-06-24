"""Digitale-PDF-loader — extraheert de tekstlaag (ingest-spec).

PDF's met een tekstlaag worden `pdf_digital` met de geëxtraheerde tekst. PDF's zonder
bruikbare tekstlaag krijgen `pdf_scanned` en lege tekst; OCR is buiten scope voor deze change
(ingest emit het bijbehorende audit-event, niet de loader — die kent de audit-log niet).

Elk document draagt extractie-gezondheid (`char_count`/`parse_ok`/`redaction_ratio`) in de
metadata, zodat de validity-gate deterministisch beslist zonder het bestand te heropenen. Een
onleesbare/corrupte PDF wordt niet weggegooid maar als document met `parse_ok=false` vastgelegd
— de validity-gate handelt het af, niet de loader.
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from zeef.health import health_metadata
from zeef.ids import content_id
from zeef.models import Document
from zeef.normalize import normalize_text


class PdfLoader:
    """Laadt één PDF naar één `Document` (pdf_digital of pdf_scanned)."""

    def can_load(self, path: Path) -> bool:
        return path.suffix.lower() == ".pdf"

    def load(self, path: Path) -> list[Document]:
        raw, parse_ok, error = _extract_text(path)
        text = normalize_text(raw)
        doc_type = "pdf_digital" if text else "pdf_scanned"
        meta: dict[str, object] = {"filename": path.name}
        meta.update(health_metadata(text, parse_ok))
        if not parse_ok:
            meta["parse_error"] = error
        if parse_ok and doc_type == "pdf_scanned":
            meta["ocr"] = "out-of-scope"
        return [Document(
            id=content_id(text, str(path)),
            source_path=str(path),
            doc_type=doc_type,
            metadata=meta,
            text=text,
        )]


def _extract_text(path: Path) -> tuple[str, bool, str]:
    """Geef (tekst, parse_ok, foutmelding). Een corrupte PDF faalt zacht: parse_ok=False.

    Breed `except Exception`: pypdf gooit op vijandige/kapotte invoer ook niet-pypdf-fouten
    (`KeyError`, `struct.error`, `RecursionError`, …). Zou de gate die niet vangen, dan valt
    het door naar ingest's brede catch en wordt het document stilletjes *gedropt* i.p.v. als
    `parse_ok=false` vastgelegd — precies de "recorded, not dropped"-eis die deze stage borgt.
    """
    try:
        reader = PdfReader(str(path))
        parts = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(parts), True, ""
    except Exception as exc:  # noqa: BLE001 — een corrupte PDF mag de run niet stoppen
        return "", False, str(exc)
