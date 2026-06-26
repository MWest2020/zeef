"""Rerank-stage (retrieve-spec, converge-ranking D14/D22): precisie-herrangschikking als side-score.

De `RerankerProvider` (cross-encoder of LLM-as-reranker; soeverein: de lexicale reranker) geeft
per kandidaat een relevantiescore t.o.v. de zoekvraag. Die score landt als `rerank` in
`Document.scores` — **puur ter inspectie**. De rerank-score is **geen** selector meer en raakt
`final` niet aan: de selectie beslist op de passage-cosine (`final`, gezet in retrieve). De
kandidaten komen gesorteerd op de rerank-score terug, maar die volgorde is niet leidend voor de
selectie (select sorteert zelf op `final`).
"""

from __future__ import annotations

from zeef.audit import AuditLog
from zeef.models import Document
from zeef.protocols import RerankerProvider

STAGE = "rerank"


def rerank(
    candidates: list[Document], reranker: RerankerProvider, audit: AuditLog, query: str
) -> list[Document]:
    """Zet de `rerank` side-score per document (inspectie); raakt `final` niet aan."""
    if not candidates:
        audit.event(STAGE, "rerank", inputs={"query": query, "candidates": 0})
        return []
    scores = reranker.rerank(query, [d.text for d in candidates])
    for doc, score in zip(candidates, scores):
        doc.scores["rerank"] = round(float(score), 6)
    ordered = sorted(candidates, key=lambda d: d.scores.get("rerank", 0.0), reverse=True)
    audit.event(STAGE, "rerank",
                model=getattr(reranker, "name", "?"), location=getattr(reranker, "location", "?"),
                inputs={"query": query, "candidates": len(candidates),
                        "ranked": [d.id for d in ordered]})
    return ordered
