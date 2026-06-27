"""Per-stap block-extractie voor `--observe` (rendering staat in observe.py).

Pure functies, geen IO en geen rich: elke functie leest de audit-events van één stap plus een
provider-opzoeker `prov(role) -> (naam, locatie)` en geeft een dict terug met de vier velden
INPUT / OUTPUT / KEUZE / HERKOMST. Zo blijft observe.py (de renderer) los van de stap-kennis.
"""

from __future__ import annotations

from typing import Callable

Prov = Callable[[str], tuple]
_DET = "lokaal-deterministisch (geen model)"


def _sov(loc: str) -> str:
    return "🔒 soeverein (lokaal)" if loc == "local" else "☁  cloud"


def _inp(ev: list[dict], action: str) -> dict:
    for e in ev:
        if e.get("action") == action:
            return e.get("inputs", {}) or {}
    return {}


def _evt(ev: list[dict], action: str) -> dict:
    for e in ev:
        if e.get("action") == action:
            return e
    return {}


def _cnt(ev: list[dict], action: str) -> int:
    return sum(1 for e in ev if e.get("action") == action)


def _criteria(ev, prov):
    art = _inp(ev, "articulate")
    name, loc = prov("llm")
    if art:
        return {"input": f'zoekvraag: "{art.get("query", "")}"',
                "output": f"{len(art.get('criteria', []))} criteria",
                "keuze": f"opgesteld door LLM ({name})" if art.get("source") == "llm" else "fallback: ruwe zoekvraag",
                "herkomst": f"LLM lokaal of cloud — nu: {_sov(loc)}"}
    fb = _inp(ev, "fallback")
    q = (fb.get("query") or "").strip()
    inp = f'zoekvraag: "{q[:60]}{"…" if len(q) > 60 else ""}"' if q else "zoekvraag"
    return {"input": inp, "output": "criteria = ruwe zoekvraag",
            "keuze": "fallback (geen LLM / --no-llm)", "herkomst": _DET}


def _ingest(ev, prov):
    n = _inp(ev, "ingest-complete").get("document_count", 0)
    skipped = _cnt(ev, "unsupported") + _cnt(ev, "load-failed")
    keuze = "loaders per bestandstype (pdf/eml/…)"
    if skipped:
        keuze += f"; {skipped} overgeslagen (niet-ondersteund/fout)"
    return {"input": "bronmap", "output": f"{n} documenten ingelezen", "keuze": keuze, "herkomst": _DET}


def _validity(ev, prov):
    c = _inp(ev, "validity-complete")
    docs, excl, kept = c.get("documents", 0), c.get("excluded", 0), c.get("redacted_kept", 0)
    return {"input": f"{docs} documenten",
            "output": f"{docs - excl} geldig · {excl} uitgesloten" + (f" · {kept} gelakt behouden" if kept else ""),
            "keuze": f"leesbare-tekst-gate (≥{c.get('min_chars', '?')} tekens) → empty-after-ocr",
            "herkomst": _DET}


def _relate(ev, prov):
    c = _inp(ev, "relate-complete")
    _, loc = prov("embed")
    return {"input": f"{c.get('documents', 0)} documenten",
            "output": f"{c.get('duplicates', 0)} duplicaat- · {c.get('overlaps', 0)} overlap-relaties (collapse pas in select)",
            "keuze": f"MinHash-kandidaten + cosine-bevestiging (≥{c.get('near_dup_threshold', '?')})",
            "herkomst": f"MinHash lokaal; near-dup-cosine via embed — nu: {_sov(loc)}"}


def _scope_filter(ev, prov):
    c = _inp(ev, "scope-complete")
    excl, und = c.get("excluded", 0), c.get("undecided", 0)
    rules: dict[str, int] = {}
    for e in ev:
        if e.get("action") == "excluded":
            r = (e.get("inputs", {}) or {}).get("reason", "?")
            key = r.split("regel:")[1].strip(" )") if "regel:" in r else r.split(":")[0][:18]
            rules[key] = rules.get(key, 0) + 1
    uit = sum(1 for e in ev if e.get("action") == "llm-decision"
              and (e.get("inputs", {}) or {}).get("verdict", "").strip().upper().startswith("UITSLUITEN"))
    beh = sum(1 for e in ev if e.get("action") == "llm-decision") - uit
    gate_on = not c.get("no_llm", False) and (uit + beh) > 0
    name, loc = prov("llm")
    keuze = ["deterministische regels" + (" + LLM-gate" if gate_on else " (LLM-gate uit)")]
    if rules:
        top = ", ".join(f"{r}×{n}" for r, n in sorted(rules.items(), key=lambda x: -x[1])[:4])
        keuze.append(f"regels: {sum(rules.values())} uitgesloten ({top})")
    if gate_on:
        keuze.append(f"LLM-gate: {uit} UITSLUITEN / {beh} BEHOUDEN ({name}, recall-veilig)")
    herk = (f"regels lokaal; LLM-gate lokaal/cloud — nu: {_sov(loc)}"
            if gate_on else "regels lokaal-deterministisch; LLM-gate uit")
    return {"input": f"{excl + und} documenten (uit relate)",
            "output": f"{und} → retrieve · {excl} uitgesloten", "keuze": keuze, "herkomst": herk}


def _retrieve(ev, prov):
    inp = _evt(ev, "first-pass").get("inputs", {}) or {}
    ranked = inp.get("ranked", [])
    name, loc = prov("embed")
    return {"input": f"{len(ranked)} kandidaten (undecided uit scope-filter)",
            "output": f"{len(ranked)} gerangschikt op embedding-relevantie",
            "keuze": f"{inp.get('method', 'cosine')} · embedder {name}",
            "herkomst": f"embedder lokaal (Ollama) of cloud (Voyage) — nu: {_sov(loc)}"}


def _rerank(ev, prov):
    cand = _inp(ev, "rerank").get("candidates", 0)
    name, loc = prov("reranker")
    return {"input": f"{cand} kandidaten",
            "output": f"{cand} herordend (side-score; raakt 'final' niet)",
            "keuze": f"reranker {name}",
            "herkomst": f"lexicaal lokaal of cloud (Voyage) — nu: {_sov(loc)}"}


def _score(ev, prov):
    c = _inp(ev, "score-complete")
    name, loc = prov("llm")
    if c:
        return {"input": f"{c.get('candidates', 0)} kandidaten",
                "output": f"{c.get('scored', 0)} gescoord (top_k={c.get('top_k', 0)})",
                "keuze": f"LLM-relevantiescore + motivatie ({name})",
                "herkomst": f"LLM lokaal of cloud — nu: {_sov(loc)}"}
    s = _inp(ev, "skipped")
    return {"input": f"{s.get('candidates', 0)} kandidaten",
            "output": "overgeslagen — final blijft de passage-cosine",
            "keuze": s.get("reason", "geen LLM-score"), "herkomst": "geen LLM (gate uit/--no-llm)"}


def _select(ev, prov):
    c = _inp(ev, "select")
    return {"input": f"{c.get('candidates', 0)} gerangschikte kandidaten",
            "output": f"{c.get('selected', 0)} geselecteerd · {c.get('collapsed', 0)} duplicaten samengevouwen",
            "keuze": f"cosine-cutoff {c.get('mode', '?')}={c.get('value', '?')} (knie@score {c.get('cutoff_score', '?')})",
            "herkomst": _DET}


def _topics(ev, prov):
    c = _inp(ev, "topics-complete")
    if not c:
        return {"input": "geselecteerde documenten", "output": "overgeslagen (geen selectie)",
                "keuze": _inp(ev, "skipped").get("reason", "—"), "herkomst": _DET}
    src = c.get("source", "?")
    _, loc = prov("llm")
    herk = (f"clustering lokaal (scipy); labels via LLM — nu: {_sov(loc)}"
            if src == "llm" else "clustering + labels lokaal (scipy/fallback)")
    return {"input": "geselecteerde documenten",
            "output": f"{c.get('onderwerpen', 0)} onderwerpen · {c.get('deelonderwerpen', 0)} deelonderwerpen",
            "keuze": f"hiërarchische clustering (scipy); labels: {src}", "herkomst": herk}


def _summarise(ev, prov):
    c = _inp(ev, "summarise-complete")
    name, loc = prov("llm")
    if c:
        return {"input": "geselecteerde documenten",
                "output": f"{c.get('summarised', 0)} samengevat (max {c.get('max_words', '?')} woorden)",
                "keuze": f"LLM-samenvatting ({name})", "herkomst": f"LLM lokaal of cloud — nu: {_sov(loc)}"}
    return {"input": "geselecteerde documenten", "output": "overgeslagen",
            "keuze": _inp(ev, "skipped").get("reason", "geen LLM"), "herkomst": "geen LLM (--no-llm)"}


def _export(ev, prov):
    return {"input": "geselecteerde kern + alle beslissingen",
            "output": "inventory.xlsx, relations.json, criteria.json, topics.json, excluded.json, report.html, run-manifest.json, audit.jsonl",
            "keuze": "artefacten schrijven (de audit-trail is de differentiator)", "herkomst": _DET}


_BUILDERS: dict[str, Callable[[list[dict], Prov], dict]] = {
    "criteria": _criteria, "ingest": _ingest, "validity": _validity, "relate": _relate,
    "scope-filter": _scope_filter, "retrieve": _retrieve, "rerank": _rerank, "score": _score,
    "select": _select, "topics": _topics, "summarise": _summarise, "export": _export,
}


def build(stage: str, events: list[dict], prov: Prov) -> dict | None:
    """Bouw het block-dict voor één stap, of None als de stap niet getoond wordt."""
    fn = _BUILDERS.get(stage)
    return fn(events, prov) if fn else None
