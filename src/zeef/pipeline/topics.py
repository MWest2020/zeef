"""Topic-clustering (topic-clustering-spec): groepeer de kern in onderwerp/deelonderwerp.

Deterministische agglomeratieve clustering (cosine, average linkage) over de **chunk**-embeddings
uit retrieve — de eenheid waarop daadwerkelijk geëmbed is — geknipt op twee hoogtes uit **hetzelfde
dendrogram** → onderwerp (grof) en deelonderwerp (fijn, daardoor bewijsbaar genest).

Omdat een lang document chunks in meer dan één cluster kan hebben, geldt een expliciete
aggregatieregel (design T7): **meerderheid van de chunk-clusters; gelijkspel → het cluster van de
medoid-chunk (de chunk het dichtst bij het documentgemiddelde), dan het kleinste cluster-id** — zodat
de T4-belofte (precies één onderwerp + één deelonderwerp per document) hard is.

Robuust en begrensd: nul-/niet-eindige chunk-embeddings (cosine is daar ongedefinieerd — `scipy`
crasht erop) worden gefilterd; houdt een document geen bruikbare chunk over, dan gaat het
deterministisch naar "Overig". Het aantal chunks per document wordt gecapt via gelijkmatige
bemonstering (design T8) zodat de O(n²)-clustering begrensd blijft zonder de topic-verdeling te
verliezen. De LLM raakt alléén de labels (zie `topic_labels.py`); `scipy`/`numpy` worden pas binnen
de stage geïmporteerd.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

from zeef.audit import AuditLog
from zeef.models import Document
from zeef.pipeline.topic_labels import doc_freq, label_cluster
from zeef.profiles import ProviderBundle
from zeef.similarity import cosine, l2_normalize

STAGE = "topics"
OVERIG = "Overig"


def cluster_topics(
    selected: list[Document],
    providers: ProviderBundle,
    audit: AuditLog,
    *,
    onderwerp_distance: float,
    deelonderwerp_distance: float,
    min_cluster_size: int,
    max_chunks_per_doc: int,
) -> dict[str, Any]:
    """Groepeer `selected` tweelaags en geef het navigeerbare onderwerp/deelonderwerp-menu terug.

    Muteert elk document in-place (`topic`/`subtopic`). Volledig deterministisch; onder `--no-llm`
    geen enkele model-call (TF-IDF-fallbacklabels)."""
    source = "fallback" if providers.no_llm else "llm"
    if not selected:
        audit.event(STAGE, "skipped", inputs={"reason": "geen geselecteerde documenten"})
        return {"source": source, "onderwerpen": []}

    chunk_vecs: list[list[float]] = []
    positions: list[list[int]] = []  # per document de indices in `chunk_vecs` (na filter + cap)
    for doc in selected:
        idx = []
        for vec in _capped(_chunk_vectors(doc, providers.embed), max_chunks_per_doc):
            idx.append(len(chunk_vecs))
            chunk_vecs.append(vec)
        positions.append(idx)
    unembeddable = [i for i, idx in enumerate(positions) if not idx]

    onderwerp, deel = _two_level(chunk_vecs, onderwerp_distance, deelonderwerp_distance)
    doc_mean = {i: _mean([chunk_vecs[p] for p in idx]) for i, idx in enumerate(positions) if idx}
    assigned = {i: _assign(positions[i], doc_mean[i], chunk_vecs, onderwerp, deel) for i in doc_mean}

    counts = Counter(o for o, _ in assigned.values())
    overig = sorted(set(unembeddable) | {i for i, (o, _) in assigned.items()
                                         if counts[o] < min_cluster_size})
    overig_set = set(overig)
    groups: dict[int, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for i, (o, d) in assigned.items():
        if i not in overig_set:
            groups[o][d].append(i)

    df = doc_freq(selected) if providers.no_llm else None
    total = len(selected)
    onderwerpen: list[dict[str, Any]] = []
    for o in sorted(groups):
        members = _ordered([i for sub in groups[o].values() for i in sub], doc_mean)
        o_label = label_cluster([selected[i] for i in members], total, providers, audit, df)
        deelonderwerpen = []
        for d in sorted(groups[o]):
            idxs = _ordered(groups[o][d], doc_mean)
            d_label = label_cluster([selected[i] for i in idxs], total, providers, audit, df)
            for i in idxs:
                selected[i].topic, selected[i].subtopic = o_label, d_label
            deelonderwerpen.append({"label": d_label, "doc_ids": [selected[i].id for i in idxs]})
        onderwerpen.append({"label": o_label, "deelonderwerpen": deelonderwerpen})

    if overig:
        ids = [selected[i].id for i in overig]
        for i in overig:
            selected[i].topic = selected[i].subtopic = OVERIG
        onderwerpen.append({"label": OVERIG, "deelonderwerpen": [{"label": OVERIG, "doc_ids": ids}]})
        audit.event(STAGE, "overig-collapse", document_ids=ids, inputs={
            "min_cluster_size": min_cluster_size, "collapsed": len(ids),
            "unembeddable": len(unembeddable)})

    named = [o for o in onderwerpen if o["label"] != OVERIG]
    audit.event(STAGE, "topics-complete", inputs={
        "source": source, "onderwerpen": len(named),
        "deelonderwerpen": sum(len(o["deelonderwerpen"]) for o in named),
        "onderwerp_distance": onderwerp_distance, "deelonderwerp_distance": deelonderwerp_distance,
        "min_cluster_size": min_cluster_size, "max_chunks_per_doc": max_chunks_per_doc,
    })
    return {"source": source, "onderwerpen": onderwerpen}


def _chunk_vectors(doc: Document, embed) -> list[list[float]]:
    """De bruikbare chunk-embeddings uit retrieve (L2-genormaliseerd). Mist een document ze, dan
    deterministisch (her)embedden. Nul-/niet-eindige vectoren worden geweerd: cosine is daar
    ongedefinieerd en `scipy.linkage` crasht erop. Lege uitkomst → het document is niet plaatsbaar."""
    vecs = [l2_normalize(c.embedding) for c in doc.chunks if c.embedding]
    if not vecs:
        texts = [c.text for c in doc.chunks] or [doc.text or doc.source_path]
        vecs = [l2_normalize(v) for v in embed.embed(texts)]
    return [v for v in vecs if _usable(v)]


def _usable(vec: list[float]) -> bool:
    """Bruikbaar voor cosine-clustering: eindig én niet de nulvector."""
    return any(x != 0.0 for x in vec) and all(math.isfinite(x) for x in vec)


def _capped(vectors: list[list[float]], cap: int) -> list[list[float]]:
    """Begrens tot `cap` chunks via gelijkmatige bemonstering over het document (T8): behoudt de
    topic-verdeling i.p.v. de staart te droppen. ≤0 of al onder de cap → ongewijzigd."""
    if cap <= 0 or len(vectors) <= cap:
        return vectors
    step = len(vectors) / cap
    return [vectors[int(i * step)] for i in range(cap)]


def _assign(idx, mean, chunk_vecs, onderwerp, deel) -> tuple[int, int]:
    """T7: het onderwerp waar de meeste chunks vallen; het deelonderwerp is de meerderheid bínnen
    dat onderwerp. Gelijkspel → de medoid-chunk, anders het kleinste id."""
    medoid = max(idx, key=lambda p: (cosine(chunk_vecs[p], mean), -p))
    o = _majority([onderwerp[p] for p in idx], onderwerp[medoid])
    in_o = [p for p in idx if onderwerp[p] == o]
    prefer = deel[medoid] if onderwerp[medoid] == o else None
    return o, _majority([deel[p] for p in in_o], prefer)


def _majority(values: list[int], prefer: int | None) -> int:
    """Meest voorkomende waarde; bij gelijkspel `prefer` indien aanwezig, anders het kleinste id."""
    counts = Counter(values)
    top = max(counts.values())
    winners = [v for v, c in counts.items() if c == top]
    return prefer if prefer in winners else min(winners)


def _mean(vectors: list[list[float]]) -> list[float]:
    dim = len(vectors[0])
    return [sum(v[i] for v in vectors) / len(vectors) for i in range(dim)]


def _ordered(indices: list[int], doc_mean: dict[int, list[float]]) -> list[int]:
    """Cluster-leden medoid-eerst (aflopend op cosinus met het clustercentroid, tie-break op index):
    de representatieve volgorde voor de LLM-snippets. Deterministisch."""
    centroid = _mean([doc_mean[i] for i in indices])
    return sorted(indices, key=lambda i: (-cosine(doc_mean[i], centroid), i))


def _two_level(vectors, onderwerp_distance, deelonderwerp_distance) -> tuple[list[int], list[int]]:
    """Eén dendrogram, twee knip-hoogtes → onderwerp (grof) en deelonderwerp (fijn, bewijsbaar genest
    want uit dezelfde `Z`). ≤1 vector → triviaal. `scipy`/`numpy` lazy: alleen deze stage importeert."""
    if len(vectors) <= 1:
        return [1] * len(vectors), [1] * len(vectors)
    import numpy as np
    from scipy.cluster.hierarchy import fcluster, linkage

    z = linkage(np.asarray(vectors, dtype=float), method="average", metric="cosine")
    return ([int(c) for c in fcluster(z, t=onderwerp_distance, criterion="distance")],
            [int(c) for c in fcluster(z, t=deelonderwerp_distance, criterion="distance")])
