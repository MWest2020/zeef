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
from zeef.export import (
    build_report_data,
    write_criteria,
    write_excluded,
    write_inventory,
    write_manifest,
    write_relations,
    write_report_html,
    write_topics,
)
from zeef.manifest import build_manifest
from zeef.models import Criteria, Document
from zeef.observe import StageObserver
from zeef.pipeline.criteria import articulate_criteria
from zeef.pipeline.ingest import ingest
from zeef.pipeline.relate import DEFAULT_NEAR_DUP_THRESHOLD, DEFAULT_OVERLAP_THRESHOLD, relate
from zeef.pipeline.rerank import rerank
from zeef.pipeline.retrieve import retrieve
from zeef.pipeline.score import score
from zeef.pipeline.scope_filter import scope_filter
from zeef.pipeline.select import select
from zeef.pipeline.summarise import DEFAULT_SUMMARY_MAX_WORDS, summarise
from zeef.pipeline.topics import cluster_topics
from zeef.pipeline.validity import validity_gate
from zeef.profiles import ProviderBundle

DEFAULT_VALIDITY_MIN_CHARS = 50
DEFAULT_REDACTION_RATIO_THRESHOLD = 0.10
# Default clustering-drempels voor directe aanroepers/tests; de CLI geeft `Settings`-waarden door.
DEFAULT_ONDERWERP_DISTANCE = 0.8
DEFAULT_DEELONDERWERP_DISTANCE = 0.5
DEFAULT_MIN_CLUSTER_SIZE = 3
DEFAULT_MAX_CHUNKS_PER_DOC = 40
# Discover-defaults voor een vol corpus (400+), gekalibreerd op qwen3-embedding (zie
# lessons_learned.md); de converge-defaults 0.8/0.5 knippen daar alles in één cluster.
DEFAULT_DISCOVER_ONDERWERP_DISTANCE = 0.50
DEFAULT_DISCOVER_DEELONDERWERP_DISTANCE = 0.42
DEFAULT_DISCOVER_MIN_CLUSTER_SIZE = 5


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
    overlap_threshold: float = DEFAULT_OVERLAP_THRESHOLD,
    validity_min_chars: int = DEFAULT_VALIDITY_MIN_CHARS,
    redaction_ratio_threshold: float = DEFAULT_REDACTION_RATIO_THRESHOLD,
    onderwerp_distance: float = DEFAULT_ONDERWERP_DISTANCE,
    deelonderwerp_distance: float = DEFAULT_DEELONDERWERP_DISTANCE,
    min_cluster_size: int = DEFAULT_MIN_CLUSTER_SIZE,
    max_chunks_per_doc: int = DEFAULT_MAX_CHUNKS_PER_DOC,
    summary_max_words: int = DEFAULT_SUMMARY_MAX_WORDS,
    progress=None,
    observe: bool = False,
) -> RunResult:
    """Draai de volledige convergentie en schrijf de artefacten naar `out_dir`."""
    # Per-stage wall-clock vastleggen: één 'timing'-event per stage in de audit-log én een
    # geaggregeerd run-manifest. perf_counter is monotoon (immuun voor klok-aanpassingen).
    timings: list[dict[str, Any]] = []
    observer = StageObserver(audit.path, providers) if observe else None

    def run_stage(name: str, fn):
        if progress is not None:
            progress(name)
        started = time.perf_counter()
        out = fn()
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        timings.append({"stage": name, "elapsed_ms": elapsed_ms})
        audit.event(name, "timing", inputs={"elapsed_ms": elapsed_ms})
        if observer is not None:
            observer.render(name)
        return out

    run_started = datetime.now(timezone.utc)
    wall_started = time.perf_counter()

    criteria = run_stage("criteria", lambda: articulate_criteria(query, providers, audit))
    docs = run_stage("ingest", lambda: ingest(docs_dir, audit))
    run_stage("validity", lambda: validity_gate(
        docs, audit, min_chars=validity_min_chars,
        redaction_ratio_threshold=redaction_ratio_threshold))
    run_stage("relate", lambda: relate(
        docs, providers.embed, audit, near_dup_threshold=near_dup_threshold,
        overlap_threshold=overlap_threshold))
    run_stage("scope-filter", lambda: scope_filter(docs, providers, audit, query))
    candidates = run_stage("retrieve", lambda: retrieve(docs, providers.embed, audit, query))
    ranked = run_stage("rerank", lambda: rerank(candidates, providers.reranker, audit, query))
    scored = run_stage("score", lambda: score(
        ranked, criteria, providers, audit, query, top_k=score_top_k))
    selected = run_stage("select", lambda: select(
        scored, mode, value, audit, recall_bias=recall_bias))
    topics = run_stage("topics", lambda: cluster_topics(
        selected, providers, audit,
        onderwerp_distance=onderwerp_distance,
        deelonderwerp_distance=deelonderwerp_distance,
        min_cluster_size=min_cluster_size,
        max_chunks_per_doc=max_chunks_per_doc))
    run_stage("summarise", lambda: summarise(
        selected, providers, audit, max_words=summary_max_words))

    def _export() -> None:
        write_inventory(selected, out_dir / "inventory.xlsx",
                        include_summary=not providers.no_llm)
        write_relations(docs, out_dir / "relations.json")
        write_criteria(criteria, out_dir / "criteria.json")
        write_topics(topics, out_dir / "topics.json")
        write_excluded(docs, out_dir / "excluded.json")
        report = build_report_data(query, run_started.isoformat(), selected, topics, docs)
        write_report_html(report, out_dir / "report.html")

    run_stage("export", _export)
    total_ms = round((time.perf_counter() - wall_started) * 1000, 1)

    # Cloud transport-grenzen (truncatie + batching) auditbaar maken: providers die hun request
    # bounden exposen `transport_stats()`; soevereine drivers niet (dan blijft dit leeg). Eén
    # samenvattend audit-event + opname in het manifest, zodat de toegepaste caps en de
    # hoeveelheid getrunceerde input navolgbaar zijn (provider-agnostisch — geen cloud-specifieke
    # tak in de orkestratie).
    transport: dict[str, Any] = {}
    for role, prov in (("embed", providers.embed), ("reranker", providers.reranker)):
        stats = getattr(prov, "transport_stats", None)
        if callable(stats):
            transport[role] = stats()
    if transport:
        audit.event("cloud", "voyage-transport", inputs=transport)

    result = RunResult(documents=docs, selected=selected, out_dir=out_dir, criteria=criteria)
    params = {
        "recall_bias": recall_bias,
        "score_top_k": score_top_k,
        "near_dup_threshold": near_dup_threshold,
        "overlap_threshold": overlap_threshold,
        "validity_min_chars": validity_min_chars,
        "redaction_ratio_threshold": redaction_ratio_threshold,
        "onderwerp_distance": onderwerp_distance,
        "deelonderwerp_distance": deelonderwerp_distance,
        "min_cluster_size": min_cluster_size,
        "max_chunks_per_doc": max_chunks_per_doc,
        "summary_max_words": summary_max_words,
        "scope_filter_llm": providers.scope_filter_llm,
        "voyage_transport": transport or None,
    }
    manifest = build_manifest(run_started.isoformat(), query, providers, criteria, mode, value,
                              params, result.counts(), total_ms, timings)
    write_manifest(manifest, out_dir / "run-manifest.json")
    audit.event("export", "artifacts-written", inputs={
        "out_dir": str(out_dir),
        "files": ["inventory.xlsx", "relations.json", "criteria.json", "topics.json",
                  "excluded.json", "report.html", "run-manifest.json", "audit.jsonl"],
    })
    return RunResult(documents=docs, selected=selected, out_dir=out_dir,
                     criteria=criteria, manifest=manifest)
