"""Viewer-ui (viewer-ui-spec): self-contained, offline `report.html` + `excluded.json`.

Bewijst expliciet: (a) het gegenereerde rapport haalt niets extern op (geen URL/fetch/externe
script/link) — de soevereiniteitsclaim; (b) onvertrouwde tekst (summary/label/titel) wordt
geëscaped, niet als markup uitgevoerd; (c) de uitgesloten set staat per reden, validity onderscheiden
van semantisch; (d) een gelakt document toont de status uit `REDACTION_META_KEY`.
"""

import json

from zeef.export import build_report_data, write_excluded, write_report_html
from zeef.models import Document
from zeef.pipeline.validity import REDACTION_META_KEY, REDACTION_NOTE

PAYLOAD = "<script>alert(1)</script>"
_TOPICS = {"source": "llm",
           "onderwerpen": [{"label": "Subsidie", "deelonderwerpen":
                            [{"label": "Cultuur", "doc_ids": ["sel1", "sel2"]}]}]}


def _sel(doc_id, **kw):
    d = Document(id=doc_id, source_path=f"/{doc_id}.pdf", doc_type="pdf_digital")
    d.decision = "selected"
    d.scores["final"] = kw.get("final", 0.8)
    d.rationale = kw.get("rationale", "")
    d.topic, d.subtopic = "Subsidie", "Cultuur"
    if "summary" in kw:
        d.metadata["summary"] = kw["summary"]
    if kw.get("redacted"):
        d.metadata[REDACTION_META_KEY] = REDACTION_NOTE
    return d


def _oos(doc_id, reason):
    d = Document(id=doc_id, source_path=f"/{doc_id}.pdf", doc_type="pdf_digital")
    d.decision = "out_of_scope"
    d.decision_reason = reason
    return d


def _corpus():
    sel1 = _sel("sel1", summary=PAYLOAD, rationale="scoort hoog")
    sel1.add_relation("overlaps-with", "sel2", evidence="overlap cosine=0.80")
    sel2 = _sel("sel2", summary="gewone samenvatting", redacted=True)
    selected = [sel1, sel2]
    excluded = [_oos("x1", "validity:empty-after-ocr"), _oos("x2", "buiten scope: niet relevant")]
    return selected, excluded


def _report(tmp_path):
    selected, excluded = _corpus()
    data = build_report_data("subsidie cultuur", "2026-06-24T10:00:00Z",
                             selected, _TOPICS, selected + excluded)
    path = write_report_html(data, tmp_path / "report.html")
    return path.read_text(encoding="utf-8"), data


def test_report_is_offline_no_external_requests(tmp_path):
    html, _ = _report(tmp_path)
    for forbidden in ("http://", "https://", "fetch(", "XMLHttpRequest",
                      "<script src", "<link ", "@import", "cdn"):
        assert forbidden not in html, forbidden


def test_untrusted_text_is_escaped_not_live(tmp_path):
    html, _ = _report(tmp_path)
    # De payload mag niet als live tag in het bestand staan; alleen in geëscapte JSON-vorm.
    assert "<script>alert(1)" not in html
    assert "\\u003cscript\\u003ealert(1)\\u003c/script\\u003e" in html


def test_excluded_grouped_by_reason_validity_vs_semantic(tmp_path):
    selected, excluded = _corpus()
    payload = json.loads(write_excluded(selected + excluded, tmp_path / "excluded.json")
                         .read_text(encoding="utf-8"))
    assert payload["count"] == 2 and payload["validity"] == 1 and payload["semantic"] == 1
    kinds = {e["id"]: e["kind"] for e in payload["excluded"]}
    assert kinds["x1"] == "validity" and kinds["x2"] == "semantic"


def test_redaction_status_from_canonical_key(tmp_path):
    html, data = _report(tmp_path)
    assert data["documents"]["sel2"]["redaction"] == REDACTION_NOTE
    assert REDACTION_NOTE in html  # de gelakt-status staat in de inline data
