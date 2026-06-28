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
DEFAULT_OVERLAP_THRESHOLD = 0.7


def relate(
    docs: list[Document],
    embed: EmbeddingProvider,
    audit: AuditLog,
    *,
    near_dup_threshold: float = DEFAULT_NEAR_DUP_THRESHOLD,
    overlap_threshold: float = DEFAULT_OVERLAP_THRESHOLD,
    progress=None,
) -> list[Document]:
    """Bouw thread-, duplicaat- en overlap-relaties op de documenten (in-place) en retourneer ze.

    `progress` (optioneel, alleen onder `--observe`) wordt tijdens de near-dup-embedding per
    document aangeroepen met (verwerkt, totaal); puur cosmetisch, raakt de relaties niet."""
    reconstruct_threads(docs, audit)
    annotate_thread_clusters(docs)
    link_exact_duplicates(docs, audit)
    link_near_duplicates(docs, embed, audit, near_dup_threshold, overlap_threshold, progress=progress)
    audit.event(STAGE, "relate-complete", inputs={
        "documents": len(docs),
        "duplicates": sum(1 for d in docs if any(r.kind == "duplicate-of" for r in d.relations)),
        "overlaps": sum(1 for d in docs for r in d.relations if r.kind == "overlaps-with"),
        "near_dup_threshold": near_dup_threshold,
        "overlap_threshold": overlap_threshold,
    })
    return docs
