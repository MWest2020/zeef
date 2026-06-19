"""Rerank-stage (retrieve-spec): precisie-herrangschikking van de eerste-pass kandidaten.

De `RerankerProvider` (cross-encoder of LLM-as-reranker; soeverein: de lexicale reranker) geeft
per kandidaat een relevantiescore t.o.v. de zoekvraag. Die score landt als `rerank` in
`Document.scores` en voedt de `final`-score waarop de selectie beslist. De kandidaten komen
gesorteerd op `final` terug.
"""

from __future__ import annotations

from zeef.audit import AuditLog
from zeef.models import Document
from zeef.protocols import RerankerProvider

STAGE = "rerank"


def rerank(
    candidates: list[Document], reranker: RerankerProvider, audit: AuditLog, query: str
) -> list[Document]:
    """Herrangschik `candidates` op rerank-score; zet `rerank` + `final` per document."""
    if not candidates:
        audit.event(STAGE, "rerank", inputs={"query": query, "candidates": 0})
        return []
    scores = reranker.rerank(query, [d.text for d in candidates])
    for doc, score in zip(candidates, scores):
        doc.scores["rerank"] = round(float(score), 6)
        doc.scores["final"] = round(float(score), 6)
    ordered = sorted(candidates, key=lambda d: d.scores.get("final", 0.0), reverse=True)
    audit.event(STAGE, "rerank",
                model=getattr(reranker, "name", "?"), location=getattr(reranker, "location", "?"),
                inputs={"query": query, "candidates": len(candidates),
                        "ranked": [d.id for d in ordered]})
    return ordered
