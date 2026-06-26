"""Select-stage (select-spec, converge-ranking D16/D20): drie cutoff-modi, expliciete recall-bias.

`top-n` (hard aantal), `threshold` (score ≥ X) en `target` (adaptieve drempel die ~N nastreeft
en de score-'knik' rapporteert, zodat de cutoff een bewuste keuze is i.p.v. een magisch getal).
De recall-bias verschuift twijfelgevallen rond de grens richting insluiten en wordt gelogd.

Deze stage bezit de duplicaat-collapse: de volledige kandidatenset (incl. duplicaten) wordt op
`final` (de passage-cosine) gerangschikt; pas dán wordt binnen elke `duplicate-of`-groep de
**hoogst gerangschikte** als representant gehouden en de rest gecollapst met een gelogde reden
(converge-ranking D16). De top-N telt dus representanten — N distincte documenten. Ranking-eerst,
representant-daarna houdt de invariant "de cosine rangschikt de volledige set" intact (D20.5).
"""

from __future__ import annotations

from zeef.audit import AuditLog
from zeef.config import CutoffMode
from zeef.models import Document

STAGE = "select"


def _final(doc: Document) -> float:
    return doc.scores.get("final", 0.0)


def _ordered(candidates: list[Document]) -> list[Document]:
    # Deterministisch: aflopend op final, daarna op id als tie-break.
    return sorted(candidates, key=lambda d: (-_final(d), d.id))


def _group_root(doc: Document, by_id: dict[str, Document]) -> str:
    """Volg `duplicate-of` tot het wortel-document (de niet-representant wijst naar de representant).
    Bewaakt tegen cykels/ontbrekende targets, zodat de groepering altijd termineert."""
    seen: set[str] = set()
    cur = doc
    while True:
        target = next((r.target_id for r in cur.relations if r.kind == "duplicate-of"), None)
        if target is None or target in seen or target not in by_id:
            return cur.id
        seen.add(target)
        cur = by_id[target]


def _collapse_duplicates(candidates: list[Document], audit: AuditLog) -> list[Document]:
    """Collapse elke `duplicate-of`-groep ná ranking: hoogste `final` is representant (tie-break op
    `source_path` — query-onafhankelijk en stabiel, want exacte duplicaten delen geen content-id maar
    wél tekst). Niet-representanten worden `out_of_scope` met gelogde reden; de relatie blijft staan
    (zichtbaar, niet stil gedropt). Geeft de representanten terug."""
    by_id = {d.id: d for d in candidates}
    groups: dict[str, list[Document]] = {}
    for doc in candidates:
        groups.setdefault(_group_root(doc, by_id), []).append(doc)
    representatives: list[Document] = []
    for members in groups.values():
        if len(members) == 1:
            representatives.append(members[0])
            continue
        rep, *rest = sorted(members, key=lambda d: (-_final(d), d.source_path))
        representatives.append(rep)
        for dup in rest:
            reason = (f"duplicaat van representant {rep.id}; gecollapst na ranking "
                      f"(final={_final(dup):.4f})")
            dup.decision = "out_of_scope"
            dup.decision_reason = reason
            audit.event(STAGE, "excluded", document_ids=[dup.id], inputs={
                "reason": reason, "representative": rep.id, "rep_final": round(_final(rep), 6),
            })
    return representatives


def select(
    candidates: list[Document],
    mode: CutoffMode,
    value: float | int,
    audit: AuditLog,
    *,
    recall_bias: float = 0.0,
) -> list[Document]:
    """Collapse duplicaten ná ranking, markeer de gekozen kern als `selected` en geef die terug."""
    representatives = _collapse_duplicates(candidates, audit)
    ordered = _ordered(representatives)
    cut_score, knee = _cutoff(ordered, mode, value)
    selected: list[Document] = []
    for doc in ordered:
        score = _final(doc)
        biased = score < cut_score and score >= cut_score - recall_bias and recall_bias > 0.0
        if score >= cut_score or biased:
            reason = f"{mode.value}={value}; final={score:.4f} ≥ cutoff={cut_score:.4f}"
            if biased:
                reason += f"; ingesloten via recall-bias {recall_bias}"
            doc.decision = "selected"
            doc.decision_reason = reason
            selected.append(doc)
    audit.event(STAGE, "select", document_ids=[d.id for d in selected], inputs={
        "mode": mode.value, "value": value, "cutoff_score": round(cut_score, 6),
        "recall_bias": recall_bias, "knee": knee, "candidates": len(ordered),
        "collapsed": len(candidates) - len(representatives), "selected": len(selected),
    })
    return selected


def _cutoff(ordered: list[Document], mode: CutoffMode, value: float | int) -> tuple[float, dict | None]:
    """Bepaal de score-drempel waarop wordt geselecteerd, plus eventueel de knik-info."""
    scores = [_final(d) for d in ordered]
    if mode is CutoffMode.threshold:
        return float(value), None
    if mode is CutoffMode.top_n:
        n = int(value)
        if n <= 0 or not scores:
            return float("inf"), None
        return scores[min(n, len(scores)) - 1], None
    if mode is CutoffMode.target:
        return _target_cutoff(scores, int(value))
    raise ValueError(f"onbekende cutoff-modus: {mode!r}")


def _target_cutoff(scores: list[float], target: int) -> tuple[float, dict | None]:
    """Adaptieve drempel rond `target`: kies de grootste score-gap (de 'knik') in een venster."""
    n = len(scores)
    if n == 0:
        return float("inf"), None
    if n <= target:
        return scores[-1], {"index": n, "note": "minder kandidaten dan target; alles geselecteerd"}
    window = max(5, target // 4)
    lo, hi = max(1, target - window), min(n - 1, target + window)
    best_idx, best_gap = target, -1.0
    for i in range(lo, hi + 1):
        gap = scores[i - 1] - scores[i]
        if gap > best_gap:
            best_gap, best_idx = gap, i
    return scores[best_idx - 1], {
        "index": best_idx, "gap": round(best_gap, 6),
        "last_selected": round(scores[best_idx - 1], 6), "first_dropped": round(scores[best_idx], 6),
    }
