"""Retrieve-stage (retrieve-spec, converge-ranking D15/D22): chunk → embed → relevantie t.o.v. de
zoekvraag.

Kandidaten zijn alle niet-uitgesloten documenten met tekst. Elk wordt gechunkt en geëmbed;
de relevantie (`embed_sim`) is de hoogste cosinus tussen de zoekvraag en de chunks — de
cosine van de best-matchende passage. Die score wordt **als `final` op elke kandidaat** gezet:
het is de enige, auditbare selector (converge-ranking). Geen latere stage (rerank/score)
overschrijft `final` of demoveert een kandidaat — de cosine rangschikt de volledige set.
De best-matchende chunk wordt als `best_passage` bewaard: de deterministische "why" (D23).
Optioneel wordt een lexicale BM25-achtige score bijgemengd (`hybrid_alpha`); default 0
houdt het zuiver vectorieel en volledig deterministisch.
"""

from __future__ import annotations

from typing import Callable

from zeef.audit import AuditLog
from zeef.drivers.local import LexicalReranker
from zeef.models import Document
from zeef.pipeline.chunking import DEFAULT_CHUNK_SIZE, chunk_document
from zeef.protocols import EmbeddingProvider
from zeef.similarity import cosine

STAGE = "retrieve"


def candidates_of(docs: list[Document]) -> list[Document]:
    """Documenten die de retrieval in gaan: niet uitgesloten, met tekst."""
    return [d for d in docs if d.decision != "out_of_scope" and d.text]


def embed_chunks(
    docs: list[Document], embed: EmbeddingProvider, audit: AuditLog,
    *, chunk_size: int = DEFAULT_CHUNK_SIZE, max_chunks_per_doc: int = 0,
    progress: Callable[[int, int], None] | None = None,
) -> list[Document]:
    """Chunk + embed elk valide, niet-uitgesloten document en bewáár de chunks (mét embedding) op het
    document. Voor de query-loze discover-route: zo heeft `cluster_topics` echte chunk-embeddings,
    zonder per-document lazy te herembedden. `max_chunks_per_doc` (>0) capt vóór het embedden via
    gelijkmatige bemonstering — zodat we op een groot corpus niet tienduizenden chunks embedden die de
    clustering tóch samplet. Geeft het valide, gededupliceerde corpus terug."""
    targets = candidates_of(docs)
    total = 0
    n_targets = len(targets)
    for idx, doc in enumerate(targets, start=1):
        if progress is not None:
            progress(idx, n_targets)
        chunks = chunk_document(doc, chunk_size)
        if 0 < max_chunks_per_doc < len(chunks):
            step = len(chunks) / max_chunks_per_doc
            chunks = [chunks[int(i * step)] for i in range(max_chunks_per_doc)]
        vecs = embed.embed([c.text for c in chunks])
        for chunk, vec in zip(chunks, vecs):
            chunk.embedding = vec
        doc.chunks = chunks
        total += len(chunks)
    audit.event("embed", "embed-corpus", model=getattr(embed, "name", "?"),
                location=getattr(embed, "location", "?"),
                inputs={"documents": len(targets), "chunks": total, "chunk_size": chunk_size,
                        "max_chunks_per_doc": max_chunks_per_doc})
    return targets


def retrieve(
    docs: list[Document],
    embed: EmbeddingProvider,
    audit: AuditLog,
    query: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    hybrid_alpha: float = 0.0,
    progress: Callable[[int, int], None] | None = None,
) -> list[Document]:
    """Bereken `embed_sim` per kandidaat t.o.v. `query` en geef de kandidaten terug.

    `progress` (optioneel, alleen onder `--observe`) wordt per kandidaat aangeroepen met
    (verwerkt, totaal); puur cosmetisch, raakt ranking/selectie niet.
    """
    candidates = candidates_of(docs)
    query_vec = embed.embed([query])[0]
    location = getattr(embed, "location", "?")
    model = getattr(embed, "name", "?")
    n_candidates = len(candidates)
    for idx, doc in enumerate(candidates, start=1):
        if progress is not None:
            progress(idx, n_candidates)
        chunks = chunk_document(doc, chunk_size)
        vecs = embed.embed([c.text for c in chunks])
        for chunk, vec in zip(chunks, vecs):
            chunk.embedding = vec
        sims = [cosine(query_vec, vec) for vec in vecs]
        sim = max(sims, default=0.0)
        if sims:
            # De best-matchende passage = de chunk met de hoogste cosine (ties → laagste ordinal,
            # deterministisch). Bewaard als de deterministische "why" (D23).
            best = max(range(len(sims)), key=lambda i: sims[i])
            doc.best_passage = chunks[best].text
        if hybrid_alpha > 0.0:
            sim = _hybrid(sim, query, doc, hybrid_alpha, candidates)
        doc.scores["embed_sim"] = round(sim, 6)
        # De cosine is de selector: zet 'm als `final` op élke kandidaat (converge-ranking D22).
        doc.scores["final"] = round(sim, 6)
    audit.event(STAGE, "embed", model=model, location=location,
                inputs={"query": query, "candidates": len(candidates),
                        "chunk_size": chunk_size})
    audit.event(STAGE, "first-pass", model=model, location=location, inputs={
        "query": query, "hybrid_alpha": hybrid_alpha,
        "method": "max-cosine-best-passage",  # de relevantie-regel (D21): de enige selector
        "ranked": [d.id for d in sorted(candidates, key=_embed_sim, reverse=True)],
    })
    return candidates


def _embed_sim(doc: Document) -> float:
    return doc.scores.get("embed_sim", 0.0)


def _hybrid(sim: float, query: str, doc: Document, alpha: float, candidates: list[Document]) -> float:
    """Meng vectorgelijkenis met een lexicale BM25-score (optioneel, recall-vriendelijk)."""
    lex = LexicalReranker().rerank(query, [d.text for d in candidates])
    by_id = {d.id: s for d, s in zip(candidates, lex)}
    doc.scores["bm25"] = round(by_id.get(doc.id, 0.0), 6)
    return (1 - alpha) * sim + alpha * by_id.get(doc.id, 0.0)
