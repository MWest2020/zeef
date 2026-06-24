"""Topic-clustering (topic-clustering-spec): groepeer de kern in onderwerp/deelonderwerp.

Deterministische agglomeratieve clustering (cosine, average linkage) over de **chunk**-embeddings
uit retrieve — de eenheid waarop daadwerkelijk geëmbed is — geknipt op twee hoogtes → onderwerp
(grof) en deelonderwerp (fijn, genest: een fijnere knip valt altijd binnen één grovere knip van
hetzelfde dendrogram).

Omdat een lang document chunks in meer dan één cluster kan hebben, geldt een expliciete
aggregatieregel (design T7) om de T4-belofte — precies één onderwerp + één deelonderwerp per
document — hard te maken: **meerderheid van de chunk-clusters; gelijkspel → het cluster van de
medoid-chunk (de chunk het dichtst bij het documentgemiddelde), dan het kleinste cluster-id.**
Volledig deterministisch en reproduceerbaar.

De LLM raakt alléén de labels; onder `--no-llm` vallen labels terug op distinctieve termen
(TF-IDF), zonder enige model-call (zie `topic_labels.py`). `scipy`/`numpy` worden bewust pas binnen
de stage geïmporteerd, zodat het skelet licht blijft.
"""

from __future__ import annotations

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
) -> dict[str, Any]:
    """Groepeer `selected` tweelaags en geef het navigeerbare onderwerp/deelonderwerp-menu terug.

    Muteert elk document in-place (`topic`/`subtopic`). Volledig deterministisch; onder `--no-llm`
    geen enkele model-call (TF-IDF-fallbacklabels)."""
    source = "fallback" if providers.no_llm else "llm"
    if not selected:
        audit.event(STAGE, "skipped", inputs={"reason": "geen geselecteerde documenten"})
        return {"source": source, "onderwerpen": []}

    chunk_vecs: list[list[float]] = []
    positions: list[list[int]] = []  # per document de indices in `chunk_vecs`
    for doc in selected:
        idx = []
        for vec in _chunk_vectors(doc, providers.embed):
            idx.append(len(chunk_vecs))
            chunk_vecs.append(vec)
        positions.append(idx)

    onderwerp = _flat_clusters(chunk_vecs, onderwerp_distance)
    deel = _flat_clusters(chunk_vecs, deelonderwerp_distance)
    doc_mean = [_mean([chunk_vecs[p] for p in idx]) for idx in positions]
    assigned = [_assign(positions[i], doc_mean[i], chunk_vecs, onderwerp, deel)
                for i in range(len(selected))]

    doc_counts = Counter(o for o, _ in assigned)
    overig = sorted(i for i, (o, _) in enumerate(assigned) if doc_counts[o] < min_cluster_size)
    overig_set = set(overig)
    groups: dict[int, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for i, (o, d) in enumerate(assigned):
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
        audit.event(STAGE, "overig-collapse", document_ids=ids,
                    inputs={"min_cluster_size": min_cluster_size, "collapsed": len(ids)})

    named = [o for o in onderwerpen if o["label"] != OVERIG]
    audit.event(STAGE, "topics-complete", inputs={
        "source": source, "onderwerpen": len(named),
        "deelonderwerpen": sum(len(o["deelonderwerpen"]) for o in named),
        "onderwerp_distance": onderwerp_distance, "deelonderwerp_distance": deelonderwerp_distance,
        "min_cluster_size": min_cluster_size,
    })
    return {"source": source, "onderwerpen": onderwerpen}


def _chunk_vectors(doc: Document, embed) -> list[list[float]]:
    """De chunk-embeddings uit retrieve (L2-genormaliseerd). Mist een document ze, dan
    deterministisch (her)embedden via de provider — zodat de stage nooit op een lege set valt."""
    vecs = [l2_normalize(c.embedding) for c in doc.chunks if c.embedding]
    if vecs:
        return vecs
    texts = [c.text for c in doc.chunks] or [doc.text or doc.source_path]
    return [l2_normalize(v) for v in embed.embed(texts)]


def _assign(idx, mean, chunk_vecs, onderwerp, deel) -> tuple[int, int]:
    """T7: ken het document toe aan het onderwerp waar de meeste van zijn chunks vallen; het
    deelonderwerp is de meerderheid bínnen dat onderwerp. Gelijkspel → de medoid-chunk, dan id."""
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


def _ordered(indices: list[int], doc_mean: list[list[float]]) -> list[int]:
    """Cluster-leden medoid-eerst: aflopend op cosinus met het clustercentroid (tie-break op index).
    Bepaalt de representatieve volgorde voor de LLM-snippets; deterministisch."""
    centroid = _mean([doc_mean[i] for i in indices])
    return sorted(indices, key=lambda i: (-cosine(doc_mean[i], centroid), i))


def _flat_clusters(vectors: list[list[float]], distance: float) -> list[int]:
    """Platte clusters waarbinnen de cofenetische cosinus-afstand ≤ `distance` blijft. ≤1 vector →
    triviaal. `scipy`/`numpy` lazy: alleen deze stage betaalt de import."""
    if len(vectors) <= 1:
        return [1] * len(vectors)
    import numpy as np
    from scipy.cluster.hierarchy import fcluster, linkage

    linkage_matrix = linkage(np.asarray(vectors, dtype=float), method="average", metric="cosine")
    return [int(c) for c in fcluster(linkage_matrix, t=distance, criterion="distance")]
