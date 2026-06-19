"""Pijplijn-orkestratie: rijg de stages aaneen (cli-spec).

ingest → relate → scope-filter → retrieve → rerank → select → export, met geïnjecteerde
providers. Deze functie kent geen concrete drivers en geen profiel; ze krijgt de
`ProviderBundle` binnen. Houdt de CLI dun en is los testbaar (zonder Typer).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from zeef.audit import AuditLog
from zeef.config import CutoffMode
from zeef.export import write_criteria, write_inventory, write_relations
from zeef.models import Criteria, Document
from zeef.pipeline.criteria import articulate_criteria
from zeef.pipeline.ingest import ingest
from zeef.pipeline.relate import DEFAULT_NEAR_DUP_THRESHOLD, relate
from zeef.pipeline.rerank import rerank
from zeef.pipeline.retrieve import retrieve
from zeef.pipeline.score import score
from zeef.pipeline.scope_filter import scope_filter
from zeef.pipeline.select import select
from zeef.profiles import ProviderBundle


@dataclass(frozen=True)
class RunResult:
    """Uitkomst van één convergentie-run, voor samenvatting en tests."""

    documents: list[Document]
    selected: list[Document]
    out_dir: Path
    criteria: Criteria

    def counts(self) -> dict[str, int]:
        sel = sum(1 for d in self.documents if d.decision == "selected")
        oos = sum(1 for d in self.documents if d.decision == "out_of_scope")
        und = sum(1 for d in self.documents if d.decision == "undecided")
        return {"total": len(self.documents), "selected": sel,
                "out_of_scope": oos, "undecided": und}


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
    progress=None,
) -> RunResult:
    """Draai de volledige convergentie en schrijf de artefacten naar `out_dir`."""
    def step(name: str) -> None:
        if progress is not None:
            progress(name)

    step("criteria")
    criteria = articulate_criteria(query, providers, audit)
    step("ingest")
    docs = ingest(docs_dir, audit)
    step("relate")
    relate(docs, providers.embed, audit, near_dup_threshold=near_dup_threshold)
    step("scope-filter")
    scope_filter(docs, providers, audit, query)
    step("retrieve")
    candidates = retrieve(docs, providers.embed, audit, query)
    step("rerank")
    ranked = rerank(candidates, providers.reranker, audit, query)
    step("score")
    scored = score(ranked, criteria, providers, audit, query, top_k=score_top_k)
    step("select")
    selected = select(scored, mode, value, audit, recall_bias=recall_bias)
    step("export")
    write_inventory(selected, out_dir / "inventory.xlsx")
    write_relations(docs, out_dir / "relations.json")
    write_criteria(criteria, out_dir / "criteria.json")
    audit.event("export", "artifacts-written", inputs={
        "out_dir": str(out_dir),
        "files": ["inventory.xlsx", "relations.json", "criteria.json", "audit.jsonl"],
    })
    return RunResult(documents=docs, selected=selected, out_dir=out_dir, criteria=criteria)
