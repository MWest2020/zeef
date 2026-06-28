"""Duplicaatdetectie (relate-spec, design.md D5): exact via tekst-hash, near-dup via MinHash+cosine.

Exacte duplicaten hebben identieke genormaliseerde tekst (de content-id verschilt omdat het
herkomstpad meeloopt, D2). Near-duplicaten worden eerst als kandidaat gegenereerd met MinHash
en pas bevestigd door embedding-cosinus boven een drempel. De niet-representatieve dubbel krijgt
een `duplicate-of`-relatie naar de representant (laagste bronpad), zodat de scope-filter er
precies één telt.
"""

from __future__ import annotations

import hashlib

from zeef.audit import AuditLog
from zeef.models import Document
from zeef.protocols import EmbeddingProvider
from zeef.similarity import cosine, tokenize

STAGE = "relate"


def _is_dup(doc: Document) -> bool:
    return any(r.kind == "duplicate-of" for r in doc.relations)


def link_exact_duplicates(docs: list[Document], audit: AuditLog) -> None:
    """Groepeer op tekst-hash; niet-representanten krijgen `duplicate-of` → representant."""
    by_hash: dict[str, list[Document]] = {}
    for doc in docs:
        if not doc.text:
            continue
        digest = hashlib.sha256(doc.text.encode("utf-8")).hexdigest()
        by_hash.setdefault(digest, []).append(doc)
    for digest, group in by_hash.items():
        if len(group) < 2:
            continue
        rep, *rest = sorted(group, key=lambda d: d.source_path)
        for dup in rest:
            dup.add_relation("duplicate-of", rep.id, evidence=f"identieke inhoud (sha256:{digest[:12]})")
            audit.event(STAGE, "duplicate", document_ids=[dup.id, rep.id],
                        inputs={"kind": "exact", "hash": digest[:12]})


def link_near_duplicates(
    docs: list[Document], embed: EmbeddingProvider, audit: AuditLog, threshold: float,
    overlap_threshold: float = 1.0, *, progress=None,
) -> None:
    """Bevestig MinHash-kandidaten met embedding-cosinus. `cos ≥ threshold` → `duplicate-of`; daar
    net onder, in `[overlap_threshold, threshold)` → `overlaps-with` (partiële overlap, geen
    duplicaat). Een `overlap_threshold ≥ threshold` (default 1.0) zet de overlap-band uit."""
    candidates = _minhash_candidate_pairs(docs)
    if candidates is None:
        audit.event(STAGE, "near-dup-skipped", inputs={"reason": "datasketch niet beschikbaar"})
        return
    targets = [d for d in docs if d.text]
    vecs = {d.id: v for d, v in zip(targets, embed.embed([d.text for d in targets], progress=progress))}
    model = getattr(embed, "name", "?")
    for a, b in candidates:
        if _is_dup(a) or _is_dup(b) or a.id not in vecs or b.id not in vecs:
            continue
        cos = cosine(vecs[a.id], vecs[b.id])
        rep, other = sorted((a, b), key=lambda d: d.source_path)
        if cos >= threshold:
            other.add_relation("duplicate-of", rep.id, evidence=f"near-duplicate cosine={cos:.3f}")
            audit.event(STAGE, "duplicate", document_ids=[other.id, rep.id],
                        inputs={"kind": "near", "cosine": round(cos, 4), "embed_model": model})
        elif cos >= overlap_threshold:
            other.add_relation("overlaps-with", rep.id, evidence=f"overlap cosine={cos:.3f}")
            audit.event(STAGE, "overlap", document_ids=[other.id, rep.id],
                        inputs={"cosine": round(cos, 4), "embed_model": model})


def _shingles(text: str, k: int = 3) -> set[str]:
    toks = tokenize(text)
    if len(toks) < k:
        return set(toks)
    return {" ".join(toks[i : i + k]) for i in range(len(toks) - k + 1)}


def _minhash_candidate_pairs(docs: list[Document]) -> list[tuple[Document, Document]] | None:
    try:
        from datasketch import MinHash, MinHashLSH
    except ImportError:  # pragma: no cover - datasketch is een core-dep
        return None
    targets = [d for d in docs if d.text]
    lsh = MinHashLSH(threshold=0.5, num_perm=128)
    mh_by_id: dict[str, object] = {}
    for doc in targets:
        mh = MinHash(num_perm=128)
        for sh in _shingles(doc.text):
            mh.update(sh.encode("utf-8"))
        lsh.insert(doc.id, mh)
        mh_by_id[doc.id] = mh
    by_id = {d.id: d for d in targets}
    seen: set[frozenset[str]] = set()
    pairs: list[tuple[Document, Document]] = []
    for doc in targets:
        for other_id in lsh.query(mh_by_id[doc.id]):
            if other_id == doc.id:
                continue
            key = frozenset((doc.id, other_id))
            if key in seen:
                continue
            seen.add(key)
            pairs.append((doc, by_id[other_id]))
    return pairs
