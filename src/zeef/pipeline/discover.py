"""Discover-orkestratie (discover-spec): query-loze onderwerp-landkaart over het volledige corpus.

`run_discover` is `converge` zónder de query-as: `ingest` → `validity` → `relate` (dedup) → embed →
`cluster_topics` → per-cluster samenvatting. De query-gedreven stages (criteria/retrieve/rerank/
score/select) worden overgeslagen. Dezelfde clustering- en label-machinerie als `converge`, gevoed
met het volledige valide, gededupliceerde corpus i.p.v. een selectie — geen tweede implementatie.

Staat los van `run.py` puur vanwege de 200-regel-bestandslimiet; deelt verder dezelfde stages en
audit-/manifest-discipline.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zeef.audit import AuditLog
from zeef.export import write_discover_map, write_discover_report, write_manifest
from zeef.models import Document
from zeef.pipeline.ingest import ingest
from zeef.pipeline.relate import relate
from zeef.pipeline.retrieve import embed_chunks
from zeef.pipeline.run import (
    DEFAULT_DISCOVER_DEELONDERWERP_DISTANCE,
    DEFAULT_DISCOVER_MIN_CLUSTER_SIZE,
    DEFAULT_DISCOVER_ONDERWERP_DISTANCE,
    DEFAULT_NEAR_DUP_THRESHOLD,
    DEFAULT_REDACTION_RATIO_THRESHOLD,
    DEFAULT_SUMMARY_MAX_WORDS,
    DEFAULT_VALIDITY_MIN_CHARS,
)
from zeef.pipeline.summarise import summarise_cluster
from zeef.pipeline.topics import cluster_topics
from zeef.pipeline.validity import REDACTION_META_KEY, validity_gate
from zeef.profiles import ProviderBundle

# Discover-demo-default voor de chunk-cap: 6 (cap 3 was smoke-fidelity tijdens de analyse). Lager
# dan de converge-default 40 omdat discover over een vol corpus embedt — zie lessons_learned.md.
DEFAULT_DISCOVER_MAX_CHUNKS_PER_DOC = 6


@dataclass(frozen=True)
class DiscoverResult:
    """Uitkomst van één discover-run: de documenten, de landkaart en het manifest."""

    documents: list[Document]
    out_dir: Path
    landkaart: dict[str, Any]
    manifest: dict[str, Any] | None = None

    def counts(self) -> dict[str, int]:
        onderwerpen = self.landkaart.get("onderwerpen", [])
        return {
            "documents": len(self.landkaart.get("documents", {})),
            "onderwerpen": len(onderwerpen),
            "deelonderwerpen": sum(len(o.get("deelonderwerpen", [])) for o in onderwerpen),
        }


def run_discover(
    docs_dir: Path,
    providers: ProviderBundle,
    out_dir: Path,
    audit: AuditLog,
    *,
    validity_min_chars: int = DEFAULT_VALIDITY_MIN_CHARS,
    redaction_ratio_threshold: float = DEFAULT_REDACTION_RATIO_THRESHOLD,
    near_dup_threshold: float = DEFAULT_NEAR_DUP_THRESHOLD,
    onderwerp_distance: float = DEFAULT_DISCOVER_ONDERWERP_DISTANCE,
    deelonderwerp_distance: float = DEFAULT_DISCOVER_DEELONDERWERP_DISTANCE,
    min_cluster_size: int = DEFAULT_DISCOVER_MIN_CLUSTER_SIZE,
    max_chunks_per_doc: int = DEFAULT_DISCOVER_MAX_CHUNKS_PER_DOC,
    summary_max_words: int = DEFAULT_SUMMARY_MAX_WORDS,
    progress=None,
) -> DiscoverResult:
    """Ontdek de onderwerp-landkaart van `docs_dir` zónder query en schrijf de runmap."""
    timings: list[dict[str, Any]] = []

    def run_stage(name: str, fn):
        if progress is not None:
            progress(name)
        started = time.perf_counter()
        out = fn()
        timings.append({"stage": name, "elapsed_ms": round((time.perf_counter() - started) * 1000, 1)})
        audit.event(name, "timing", inputs={"elapsed_ms": timings[-1]["elapsed_ms"]})
        return out

    run_started = datetime.now(timezone.utc)
    wall_started = time.perf_counter()

    docs = run_stage("ingest", lambda: ingest(docs_dir, audit))
    run_stage("validity", lambda: validity_gate(
        docs, audit, min_chars=validity_min_chars,
        redaction_ratio_threshold=redaction_ratio_threshold))
    run_stage("relate", lambda: relate(docs, providers.embed, audit,
                                       near_dup_threshold=near_dup_threshold))
    corpus = run_stage("embed", lambda: embed_chunks(
        docs, providers.embed, audit, max_chunks_per_doc=max_chunks_per_doc))
    topics = run_stage("topics", lambda: cluster_topics(
        corpus, providers, audit, onderwerp_distance=onderwerp_distance,
        deelonderwerp_distance=deelonderwerp_distance, min_cluster_size=min_cluster_size,
        max_chunks_per_doc=max_chunks_per_doc))

    by_id = {d.id: d for d in corpus}

    def _summaries() -> None:
        for ond in topics["onderwerpen"]:
            for deel in ond["deelonderwerpen"]:
                members = [by_id[i] for i in deel["doc_ids"] if i in by_id]
                deel["summary"] = summarise_cluster(members, providers, audit,
                                                    max_words=summary_max_words)

    run_stage("summarise", _summaries)

    documents = {d.id: {"id": d.id, "name": d.source_path.rsplit("/", 1)[-1],
                        "redaction": str(d.metadata.get(REDACTION_META_KEY, ""))} for d in corpus}
    landkaart = {"generated_at": run_started.isoformat(), "source": topics["source"],
                 "onderwerpen": topics["onderwerpen"], "documents": documents}

    def _export() -> None:
        write_discover_map(landkaart, out_dir / "discover-map.json")
        write_discover_report(landkaart, out_dir / "report.html")

    run_stage("export", _export)
    total_ms = round((time.perf_counter() - wall_started) * 1000, 1)

    result = DiscoverResult(documents=docs, out_dir=out_dir, landkaart=landkaart)
    manifest: dict[str, Any] = {
        "schema": "zeef-discover-manifest/1",
        "ts": run_started.isoformat(),
        "mode": "discover",
        "providers": {
            "embed": {"name": getattr(providers.embed, "name", "?"),
                      "location": getattr(providers.embed, "location", "?")},
            "llm": {"name": getattr(providers.llm, "name", "?"),
                    "location": getattr(providers.llm, "location", "?"),
                    "enabled": not providers.no_llm},
        },
        "params": {
            "embed_source": getattr(providers.embed, "name", "?"),
            "near_dup_threshold": near_dup_threshold,
            "onderwerp_distance": onderwerp_distance,
            "deelonderwerp_distance": deelonderwerp_distance,
            "min_cluster_size": min_cluster_size,
            "max_chunks_per_doc": max_chunks_per_doc,
            "summary_max_words": summary_max_words,
            "validity_min_chars": validity_min_chars,
            "redaction_ratio_threshold": redaction_ratio_threshold,
        },
        "counts": {**result.counts(),
                   "excluded": sum(1 for d in docs if d.decision == "out_of_scope")},
        "runtime_ms": {"total": total_ms, "stages": timings},
    }
    write_manifest(manifest, out_dir / "run-manifest.json")
    audit.event("export", "artifacts-written", inputs={
        "out_dir": str(out_dir),
        "files": ["discover-map.json", "report.html", "run-manifest.json", "audit.jsonl"],
    })
    return DiscoverResult(documents=docs, out_dir=out_dir, landkaart=landkaart, manifest=manifest)
