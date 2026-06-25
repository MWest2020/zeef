"""Run-manifest opbouw (`run-manifest.json`).

Eén plek die de geïnjecteerde providers, criteria, cutoff, parameters, tellingen en runtime tot
het machineleesbare manifest samenstelt. Apart gehouden van de orkestratie (`pipeline/run.py`)
zodat die dun en provider-agnostisch blijft; de manifest-vorm is een export-/audit-concern.
"""

from __future__ import annotations

from typing import Any

MANIFEST_SCHEMA = "zeef-run-manifest/1"


def _provider(prov: object, *, with_enabled: bool | None = None) -> dict[str, Any]:
    info = {
        "name": getattr(prov, "name", "?"),
        "location": getattr(prov, "location", "?"),
    }
    if with_enabled is not None:
        info["enabled"] = with_enabled
    return info


def build_manifest(
    ts: str,
    query: str,
    providers: Any,
    criteria: Any,
    mode: Any,
    value: float | int,
    params: dict[str, Any],
    counts: dict[str, int],
    total_ms: float,
    timings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Stel het run-manifest samen uit de reeds-berekende run-gegevens."""
    return {
        "schema": MANIFEST_SCHEMA,
        "ts": ts,
        "query": query,
        "providers": {
            "llm": _provider(providers.llm, with_enabled=not providers.no_llm),
            "embed": _provider(providers.embed),
            "reranker": _provider(providers.reranker),
        },
        "criteria": {"source": criteria.source, "labels": [c.label for c in criteria.items]},
        "cutoff": {"mode": mode.value, "value": value},
        "params": params,
        "counts": counts,
        "runtime_ms": {"total": total_ms, "stages": timings},
    }
