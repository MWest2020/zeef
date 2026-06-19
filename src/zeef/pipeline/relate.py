"""Relate-stage: thread-reconstructie + duplicaatdetectie, als getypeerde relaties (relate-spec).

Orkestreert de deterministische onderdelen (threads, exacte dubbels) en de cosinus-bevestigde
near-duplicaten. Alles wat hier wordt afgeleid landt als `Relation` op het document én als
audit-event, zodat de relatie-graaf achteraf navolgbaar is.
"""

from __future__ import annotations

from zeef.audit import AuditLog
from zeef.models import Document
from zeef.pipeline.dedup import link_exact_duplicates, link_near_duplicates
from zeef.pipeline.threads import annotate_thread_clusters, reconstruct_threads
from zeef.protocols import EmbeddingProvider

STAGE = "relate"
DEFAULT_NEAR_DUP_THRESHOLD = 0.9


def relate(
    docs: list[Document],
    embed: EmbeddingProvider,
    audit: AuditLog,
    *,
    near_dup_threshold: float = DEFAULT_NEAR_DUP_THRESHOLD,
) -> list[Document]:
    """Bouw thread- en duplicaatrelaties op de documenten (in-place) en retourneer ze."""
    reconstruct_threads(docs, audit)
    annotate_thread_clusters(docs)
    link_exact_duplicates(docs, audit)
    link_near_duplicates(docs, embed, audit, near_dup_threshold)
    audit.event(STAGE, "relate-complete", inputs={
        "documents": len(docs),
        "duplicates": sum(1 for d in docs if any(r.kind == "duplicate-of" for r in d.relations)),
        "near_dup_threshold": near_dup_threshold,
    })
    return docs
