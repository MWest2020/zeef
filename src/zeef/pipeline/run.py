"""Pijplijn-orkestratie: rijg de stages aaneen (cli-spec).

ingest → relate → scope-filter → retrieve → rerank → select → export, met geïnjecteerde
providers. Deze functie kent geen concrete drivers en geen profiel; ze krijgt de
`ProviderBundle` binnen. Houdt de CLI dun en is los testbaar (zonder Typer).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zeef.audit import AuditLog
from zeef.config import CutoffMode
from zeef.export import write_criteria, write_inventory, write_manifest, write_relations
from zeef.models import Criteria, Document
from zeef.pipeline.criteria import articulate_criteria
from zeef.pipeline.ingest import ingest
from zeef.pipeline.relate import DEFAULT_NEAR_DUP_THRESHOLD, relate
from zeef.pipeline.rerank import rerank
from zeef.pipeline.retrieve import retrieve
from zeef.pipeline.score import score
from zeef.pipeline.scope_filter import scope_filter
from zeef.pipeline.select import select
from zeef.pipeline.validity import validity_gate
from zeef.profiles import ProviderBundle

DEFAULT_VALIDITY_MIN_CHARS = 50
DEFAULT_REDACTION_RATIO_THRESHOLD = 0.10


@dataclass(frozen=True)
class RunResult:
    """Uitkomst van één convergentie-run, voor samenvatting en tests."""

    documents: list[Document]
    selected: list[Document]
    out_dir: Path
    criteria: Criteria
    manifest: dict[str, Any] | None = None

    def counts(self) -> dict[str, int]:
        sel = sum(1 for d in self.documents if d.decision == "selected")
        oos = sum(1 for d in self.documents if d.decision == "out_of_scope")
        und = sum(1 for d in self.documents if d.decision == "undecided")
        # Validity-uitsluitingen zijn een aparte, rapporteerbare categorie (validity-gate-spec):
        # mechanisch onbruikbaar, los van de semantische scope-filter-uitsluitingen.
        val = sum(1 for d in self.documents if d.decision == "out_of_scope"
                  and d.decision_reason.startswith("validity:"))
        return {"total": len(self.documents), "selected": sel,
                "out_of_scope": oos, "undecided": und, "validity_excluded": val}


def run_converge(
    docs_dir: Path,
    query: str,
    providers: ProviderBundle,
    mode: CutoffMode,
    value: float | int,
    out_dir: Path,
    audit: AuditLog,
    *,
    recall_bias: float = 0.0,
    score_top_k: int = 0,
    near_dup_threshold: float = DEFAULT_NEAR_DUP_THRESHOLD,
    validity_min_chars: int = DEFAULT_VALIDITY_MIN_CHARS,
    redaction_ratio_threshold: float = DEFAULT_REDACTION_RATIO_THRESHOLD,
    progress=None,
) -> RunResult:
    """Draai de volledige convergentie en schrijf de artefacten naar `out_dir`."""
    # Per-stage wall-clock vastleggen: één 'timing'-event per stage in de audit-log én een
    # geaggregeerd run-manifest. perf_counter is monotoon (immuun voor klok-aanpassingen).
    timings: list[dict[str, Any]] = []

    def run_stage(name: str, fn):
        if progress is not None:
            progress(name)
        started = time.perf_counter()
        out = fn()
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        timings.append({"stage": name, "elapsed_ms": elapsed_ms})
        audit.event(name, "timing", inputs={"elapsed_ms": elapsed_ms})
        return out

    run_started = datetime.now(timezone.utc)
    wall_started = time.perf_counter()

    criteria = run_stage("criteria", lambda: articulate_criteria(query, providers, audit))
    docs = run_stage("ingest", lambda: ingest(docs_dir, audit))
    run_stage("validity", lambda: validity_gate(
        docs, audit, min_chars=validity_min_chars,
        redaction_ratio_threshold=redaction_ratio_threshold))
    run_stage("relate", lambda: relate(
        docs, providers.embed, audit, near_dup_threshold=near_dup_threshold))
    run_stage("scope-filter", lambda: scope_filter(docs, providers, audit, query))
    candidates = run_stage("retrieve", lambda: retrieve(docs, providers.embed, audit, query))
    ranked = run_stage("rerank", lambda: rerank(candidates, providers.reranker, audit, query))
    scored = run_stage("score", lambda: score(
        ranked, criteria, providers, audit, query, top_k=score_top_k))
    selected = run_stage("select", lambda: select(
        scored, mode, value, audit, recall_bias=recall_bias))

    def _export() -> None:
        write_inventory(selected, out_dir / "inventory.xlsx")
        write_relations(docs, out_dir / "relations.json")
        write_criteria(criteria, out_dir / "criteria.json")

    run_stage("export", _export)
    total_ms = round((time.perf_counter() - wall_started) * 1000, 1)

    result = RunResult(documents=docs, selected=selected, out_dir=out_dir, criteria=criteria)
    manifest: dict[str, Any] = {
        "schema": "zeef-run-manifest/1",
        "ts": run_started.isoformat(),
        "query": query,
        "providers": {
            "llm": {
                "name": getattr(providers.llm, "name", "?"),
                "location": getattr(providers.llm, "location", "?"),
                "enabled": not providers.no_llm,
            },
            "embed": {
                "name": getattr(providers.embed, "name", "?"),
                "location": getattr(providers.embed, "location", "?"),
            },
            "reranker": {
                "name": getattr(providers.reranker, "name", "?"),
                "location": getattr(providers.reranker, "location", "?"),
            },
        },
        "criteria": {"source": criteria.source, "labels": [c.label for c in criteria.items]},
        "cutoff": {"mode": mode.value, "value": value},
        "params": {
            "recall_bias": recall_bias,
            "score_top_k": score_top_k,
            "near_dup_threshold": near_dup_threshold,
            "validity_min_chars": validity_min_chars,
            "redaction_ratio_threshold": redaction_ratio_threshold,
        },
        "counts": result.counts(),
        "runtime_ms": {"total": total_ms, "stages": timings},
    }
    write_manifest(manifest, out_dir / "run-manifest.json")
    audit.event("export", "artifacts-written", inputs={
        "out_dir": str(out_dir),
        "files": ["inventory.xlsx", "relations.json", "criteria.json",
                  "run-manifest.json", "audit.jsonl"],
    })
    return RunResult(documents=docs, selected=selected, out_dir=out_dir,
                     criteria=criteria, manifest=manifest)
