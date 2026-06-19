"""Ingest & normalisatie (ingest-spec): loaderselectie, headers, bijlagen, scanned PDF."""

import json

from zeef.loaders import EmailLoader, PdfLoader, default_loaders, select_loader
from zeef.pipeline.ingest import ingest


def _events(audit):
    return [json.loads(line) for line in audit.path.read_text(encoding="utf-8").splitlines()]


def test_loader_selected_by_file_type(corpus):
    loaders = default_loaders()
    assert isinstance(select_loader(corpus / "thread-01.eml", loaders), EmailLoader)
    assert isinstance(select_loader(corpus / "memo-begroting.pdf", loaders), PdfLoader)
    assert select_loader(corpus / "leesmij.xyz", loaders) is None


def test_unsupported_file_recorded_not_fatal(corpus, audit):
    docs = ingest(corpus, audit)
    events = _events(audit)
    unsupported = [e for e in events if e["action"] == "unsupported"]
    assert any("leesmij.xyz" in e["inputs"]["path"] for e in unsupported)
    # De run gaat door: er zijn gewoon documenten geladen.
    assert len(docs) > 0


def test_threading_headers_retained(corpus, audit):
    docs = {d.source_path.split("/")[-1]: d for d in ingest(corpus, audit)}
    t1 = docs["thread-01.eml"]
    t2 = docs["thread-02.eml"]
    assert t1.metadata["Message-ID"] == "<m1@zeef.test>"
    assert t2.metadata["In-Reply-To"] == "<m1@zeef.test>"
    assert "<m1@zeef.test>" in t2.metadata["References"]


def test_attachment_becomes_linked_document(corpus, audit):
    docs = ingest(corpus, audit)
    parent = next(d for d in docs if d.source_path.endswith("mail-met-bijlage.eml"))
    attachments = [d for d in docs if d.metadata.get("attachment_of") == parent.id]
    assert len(attachments) == 1
    att = attachments[0]
    rels = [r for r in att.relations if r.kind == "attachment-of"]
    assert rels and rels[0].target_id == parent.id
    assert att.metadata["filename"] == "notitie-budget.txt"


def test_digital_pdf_yields_text(corpus, audit):
    docs = ingest(corpus, audit)
    pdf = next(d for d in docs if d.source_path.endswith("memo-begroting.pdf"))
    assert pdf.doc_type == "pdf_digital"
    assert "subsidie cultuur" in pdf.text


def test_scanned_pdf_flagged_and_audited(corpus, audit):
    docs = ingest(corpus, audit)
    scan = next(d for d in docs if d.source_path.endswith("scan-zonder-tekst.pdf"))
    assert scan.doc_type == "pdf_scanned"
    assert scan.text == ""
    ocr_events = [e for e in _events(audit) if e["action"] == "ocr-out-of-scope"]
    assert any(scan.id in e["document_ids"] for e in ocr_events)
