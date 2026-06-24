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

# `category` draagt nu het onderwerp/deelonderwerp (topic-clustering), niet het bestandstype;
# dat laatste blijft behouden in een eigen `doc_type`-kolom zodat geen informatie verloren gaat.
INVENTORY_COLUMNS = ("id", "score", "category", "doc_type", "summary", "reason", "motivatie")


def _category(doc: Document) -> str:
    """Onderwerp / deelonderwerp als één cel; valt terug op alleen het onderwerp (of leeg)."""
    if doc.subtopic and doc.subtopic != doc.topic:
        return f"{doc.topic} / {doc.subtopic}"
    return doc.topic


def write_inventory(selected: list[Document], path: Path) -> Path:
    """Schrijf de kernselectie naar `inventory.xlsx` met de vaste kolommen."""
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "inventory"
    ws.append(list(INVENTORY_COLUMNS))
    for doc in selected:
        ws.append([
            doc.id,
            round(doc.scores.get("final", 0.0), 6),
            _category(doc),
            doc.doc_type,
            str(doc.metadata.get("summary", "")),
            doc.decision_reason,
            doc.rationale,
        ])
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
