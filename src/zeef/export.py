"""Export (export-spec): inventory.xlsx, relations.json, criteria.json en de audit-log.

De inventory bevat per geselecteerd document id, score, categorie, samenvatting, reden en
motivatie; samenvatting en motivatie blijven leeg als er geen LLM is gedraaid (`--no-llm`).
De relatie-graaf en de gearticuleerde relevantiecriteria worden als JSON weggeschreven.
`audit.jsonl` staat al in de run-map (de stages schrijven er direct heen).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openpyxl import Workbook

from zeef.models import Criteria, Document
from zeef.pipeline.validity import REDACTION_META_KEY

# Single-file HTML-template + de marker waar de inline run-data in wordt geïnjecteerd.
_REPORT_TEMPLATE = Path(__file__).parent / "templates" / "report.html"
_DATA_MARKER = "__ZEEF_DATA__"

# `category` draagt nu het onderwerp/deelonderwerp (topic-clustering), niet het bestandstype;
# dat laatste blijft behouden in een eigen `doc_type`-kolom zodat geen informatie verloren gaat.
INVENTORY_COLUMNS = ("id", "score", "category", "doc_type", "summary", "reason", "motivatie")


# Tekens die Excel/LibreOffice (en openpyxl) als formule-start zien: een cel die hiermee begint
# wordt uitgevoerd bij openen (CSV/Excel-formule-injectie, CWE-1236). Inhoud uit onvertrouwde bron
# (LLM-samenvatting/labels, documenttekst) wordt door een ambtenaar in Excel geopend.
_FORMULA_LEAD = ("=", "+", "-", "@", "\t", "\r")


def _category(doc: Document) -> str:
    """Onderwerp / deelonderwerp als één cel; valt terug op alleen het onderwerp (of leeg)."""
    if doc.subtopic and doc.subtopic != doc.topic:
        return f"{doc.topic} / {doc.subtopic}"
    return doc.topic


def _formula_safe(value: object) -> object:
    """Neutraliseer formule-injectie: prefix een tekstcel die met een formule-teken begint met een
    apostrof, zodat Excel/LibreOffice 'm als tekst toont i.p.v. uit te voeren. Niet-tekst ongemoeid."""
    if isinstance(value, str) and value[:1] in _FORMULA_LEAD:
        return "'" + value
    return value


def write_inventory(selected: list[Document], path: Path, *, include_summary: bool = True) -> Path:
    """Schrijf de kernselectie naar `inventory.xlsx`. De `summary`-kolom verschijnt alleen wanneer er
    samenvattingen zijn (LLM); onder `--no-llm` wordt ze weggelaten i.p.v. leeg getoond."""
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = INVENTORY_COLUMNS if include_summary else tuple(
        c for c in INVENTORY_COLUMNS if c != "summary")
    wb = Workbook()
    ws = wb.active
    ws.title = "inventory"
    ws.append(list(columns))
    for doc in selected:
        cells = {
            "id": doc.id,
            "score": round(doc.scores.get("final", 0.0), 6),
            "category": _category(doc),
            "doc_type": doc.doc_type,
            "summary": str(doc.metadata.get("summary", "")),
            "reason": doc.decision_reason,
            "motivatie": doc.rationale,
        }
        ws.append([_formula_safe(cells[c]) for c in columns])
    wb.save(path)
    return path


def write_topics(topics: dict, path: Path) -> Path:
    """Schrijf het onderwerp/deelonderwerp-menu naar `topics.json` (het keuzemenu voor de verzoeker)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(topics, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_criteria(criteria: Criteria, path: Path) -> Path:
    """Schrijf de gearticuleerde relevantiecriteria naar `criteria.json` (inspecteerbaar)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        criteria.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return path


def write_manifest(manifest: dict[str, Any], path: Path) -> Path:
    """Schrijf het run-manifest naar `run-manifest.json`: de vastgelegde runtimes per stage en
    de run-parameters (zoekvraag, providers/model/locatie, criteria-bron, cutoff, telling). Maakt
    een run navolgbaar en vergelijkbaar zónder de volledige audit-log te hoeven herleiden."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _doc_name(doc: Document) -> str:
    return doc.source_path.rsplit("/", 1)[-1]


def _excluded_entry(doc: Document) -> dict:
    """Eén uitgesloten document, met reden-categorie: validity (mechanisch) vs semantisch."""
    kind = "validity" if doc.decision_reason.startswith("validity:") else "semantic"
    return {"id": doc.id, "name": _doc_name(doc), "doc_type": doc.doc_type,
            "reason": doc.decision_reason, "kind": kind,
            "redaction": str(doc.metadata.get(REDACTION_META_KEY, ""))}


def write_excluded(docs: list[Document], path: Path) -> Path:
    """Schrijf de volledige uitgesloten set + redenen machine-leesbaar naar `excluded.json`
    (de 'rest' naast de kern; validity onderscheiden van semantische out-of-scope)."""
    entries = [_excluded_entry(d) for d in docs if d.decision == "out_of_scope"]
    payload = {"excluded": entries, "count": len(entries),
               "validity": sum(1 for e in entries if e["kind"] == "validity"),
               "semantic": sum(1 for e in entries if e["kind"] == "semantic")}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def build_report_data(query: str, generated_at: str, selected: list[Document], topics: dict,
                      all_docs: list[Document]) -> dict:
    """Bouw het presentatie-model voor het rapport — alléén presentatievelden (geen documenttekst).
    Redactie-status komt uit de canonieke `REDACTION_META_KEY`, niet uit `decision_reason`."""
    documents = {
        d.id: {
            "id": d.id, "name": _doc_name(d), "score": round(d.scores.get("final", 0.0), 4),
            "rationale": d.rationale, "summary": str(d.metadata.get("summary", "")),
            "reason": d.decision_reason, "doc_type": d.doc_type,
            "topic": d.topic, "subtopic": d.subtopic,
            "redaction": str(d.metadata.get(REDACTION_META_KEY, "")),
            "relations": [{"kind": r.kind, "target": r.target_id, "evidence": r.evidence}
                          for r in d.relations],
        }
        for d in selected
    }
    excluded = [_excluded_entry(d) for d in all_docs if d.decision == "out_of_scope"]
    counts = {
        "total": len(all_docs), "selected": len(documents), "out_of_scope": len(excluded),
        "validity_excluded": sum(1 for e in excluded if e["kind"] == "validity"),
        "undecided": sum(1 for d in all_docs if d.decision == "undecided"),
    }
    return {"query": query, "generated_at": generated_at, "counts": counts,
            "topics": topics, "documents": documents, "excluded": excluded}


def write_report_html(data: dict, path: Path) -> Path:
    """Injecteer de run-data inline in het single-file template en schrijf `report.html`. De JSON
    wordt `<` / `>` / `&`-geëscaped zodat documentinhoud het `<script>`-blok nooit kan afsluiten
    (JSON.parse herstelt de `\\u00xx`-escapes in de browser). Geen netwerk, opent via `file://`."""
    blob = json.dumps(data, ensure_ascii=False)
    blob = blob.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    template = _REPORT_TEMPLATE.read_text(encoding="utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template.replace(_DATA_MARKER, blob), encoding="utf-8")
    return path


def write_relations(docs: list[Document], path: Path) -> Path:
    """Schrijf de getypeerde relatie-graaf naar `relations.json`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    edges = [
        {"source": doc.id, "kind": rel.kind, "target": rel.target_id, "evidence": rel.evidence}
        for doc in docs
        for rel in doc.relations
    ]
    payload = {"edges": edges, "document_count": len(docs), "edge_count": len(edges)}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
