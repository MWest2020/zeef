"""Ingest-stage: map → genormaliseerde `Document`s, met audit per bestand (ingest-spec).

Wandelt de map deterministisch (gesorteerd pad), kiest per bestand de eerste passende loader,
en legt elke uitkomst vast in de audit-log: geladen, niet-ondersteund, of load-fout. PDF's
zonder tekstlaag (`pdf_scanned`) krijgen een expliciet 'OCR buiten scope'-event.
"""

from __future__ import annotations

from pathlib import Path

from zeef.audit import AuditLog
from zeef.loaders import default_loaders, select_loader
from zeef.models import Document
from zeef.protocols import Loader

STAGE = "ingest"


def ingest(
    docs_dir: Path, audit: AuditLog, loaders: list[Loader] | None = None
) -> list[Document]:
    """Laad alle bestanden onder `docs_dir` tot genormaliseerde `Document`s."""
    loaders = loaders if loaders is not None else default_loaders()
    documents: list[Document] = []
    for path in _iter_files(docs_dir):
        loader = select_loader(path, loaders)
        if loader is None:
            audit.event(STAGE, "unsupported", inputs={"path": str(path)})
            continue
        try:
            loaded = loader.load(path)
        except Exception as exc:  # noqa: BLE001 — één kapot bestand mag de run niet stoppen
            audit.event(STAGE, "load-failed", inputs={"path": str(path), "error": str(exc)})
            continue
        for doc in loaded:
            _record(audit, doc)
            documents.append(doc)
    audit.event(STAGE, "ingest-complete", inputs={"document_count": len(documents)})
    return documents


def _iter_files(docs_dir: Path) -> list[Path]:
    return sorted((p for p in docs_dir.rglob("*") if p.is_file()), key=str)


def _record(audit: AuditLog, doc: Document) -> None:
    audit.event(
        STAGE, "loaded", document_ids=[doc.id],
        inputs={"path": doc.source_path, "doc_type": doc.doc_type},
    )
    if doc.doc_type == "pdf_scanned":
        audit.event(
            STAGE, "ocr-out-of-scope", document_ids=[doc.id],
            inputs={"path": doc.source_path,
                    "note": "geen tekstlaag; OCR is buiten scope voor deze change"},
        )
