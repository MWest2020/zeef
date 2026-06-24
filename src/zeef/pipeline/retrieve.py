"""Retrieve-stage (retrieve-spec): chunk → embed → eerste-pass score t.o.v. de zoekvraag.

Kandidaten zijn alle niet-uitgesloten documenten met tekst. Elk wordt gechunkt en geëmbed;
de eerste-pass gelijkenis (`embed_sim`) is de hoogste cosinus tussen de zoekvraag en de
chunks. Optioneel wordt een lexicale BM25-achtige score bijgemengd (`hybrid_alpha`); default 0
houdt het zuiver vectorieel en volledig deterministisch.
"""

from __future__ import annotations

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
    *, chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> list[Document]:
    """Chunk + embed elk valide, niet-uitgesloten document en bewáár de chunks (mét embedding) op het
    document. Voor de query-loze discover-route: zo heeft `cluster_topics` echte chunk-embeddings (en
    werkt de `max_chunks_per_doc`-cap), zonder per-document lazy te herembedden. Geeft het valide,
    gededupliceerde corpus terug."""
    targets = candidates_of(docs)
    for doc in targets:
        chunks = chunk_document(doc, chunk_size)
        vecs = embed.embed([c.text for c in chunks])
        for chunk, vec in zip(chunks, vecs):
            chunk.embedding = vec
        doc.chunks = chunks
    audit.event("embed", "embed-corpus", model=getattr(embed, "name", "?"),
                location=getattr(embed, "location", "?"),
                inputs={"documents": len(targets), "chunk_size": chunk_size})
    return targets


def retrieve(
    docs: list[Document],
    embed: EmbeddingProvider,
    audit: AuditLog,
    query: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    hybrid_alpha: float = 0.0,
) -> list[Document]:
    """Bereken `embed_sim` per kandidaat t.o.v. `query` en geef de kandidaten terug."""
    candidates = candidates_of(docs)
    query_vec = embed.embed([query])[0]
    location = getattr(embed, "location", "?")
    model = getattr(embed, "name", "?")
    for doc in candidates:
        chunks = chunk_document(doc, chunk_size)
        vecs = embed.embed([c.text for c in chunks])
        for chunk, vec in zip(chunks, vecs):
            chunk.embedding = vec
        sim = max((cosine(query_vec, vec) for vec in vecs), default=0.0)
        if hybrid_alpha > 0.0:
            sim = _hybrid(sim, query, doc, hybrid_alpha, candidates)
        doc.scores["embed_sim"] = round(sim, 6)
    audit.event(STAGE, "embed", model=model, location=location,
                inputs={"query": query, "candidates": len(candidates),
                        "chunk_size": chunk_size})
    audit.event(STAGE, "first-pass", inputs={
        "query": query, "hybrid_alpha": hybrid_alpha,
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
