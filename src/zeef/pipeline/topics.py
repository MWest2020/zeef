"""Topic-clustering (topic-clustering-spec): groepeer de kern in onderwerp/deelonderwerp.

Deterministische agglomeratieve clustering (cosine, average linkage) over de reeds berekende
document-embeddings, geknipt op twee hoogtes → onderwerp (grof) en deelonderwerp (fijn, genest:
een fijnere knip valt altijd binnen één grovere knip van hetzelfde dendrogram). De groepering is
reproduceerbaar — vaste linkage + drempels → identieke input geeft identieke toewijzing. De LLM
raakt alléén de labels; onder `--no-llm` vallen labels terug op distinctieve termen (TF-IDF),
zonder enige model-call. `scipy`/`numpy` worden bewust pas binnen de stage geïmporteerd, zodat het
skelet licht blijft.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

from zeef.audit import AuditLog
from zeef.models import Document
from zeef.profiles import ProviderBundle
from zeef.similarity import l2_normalize, tokenize

STAGE = "topics"
OVERIG = "Overig"
_LABEL_TERMS = 3
_SYSTEM = "Je benoemt een groep documenten met één kort, concreet Nederlands onderwerp-label."


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

    vectors = [_doc_vector(d, providers.embed) for d in selected]
    onderwerp_ids = _flat_clusters(vectors, onderwerp_distance)
    deel_ids = _flat_clusters(vectors, deelonderwerp_distance)

    counts = Counter(onderwerp_ids)
    overig = sorted(i for i, c in enumerate(onderwerp_ids) if counts[c] < min_cluster_size)
    groups: dict[int, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    overig_set = set(overig)
    for i, (ond, deel) in enumerate(zip(onderwerp_ids, deel_ids)):
        if i not in overig_set:
            groups[ond][deel].append(i)

    df = _doc_freq(selected) if providers.no_llm else None
    onderwerpen: list[dict[str, Any]] = []
    for ond in sorted(groups):
        members = [selected[i] for deel in groups[ond].values() for i in deel]
        o_label = _label(members, selected, providers, audit, df)
        deelonderwerpen = []
        for deel in sorted(groups[ond]):
            idxs = groups[ond][deel]
            d_label = _label([selected[i] for i in idxs], selected, providers, audit, df)
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


def _doc_vector(doc: Document, embed) -> list[float]:
    """Eén vector per document: gemiddelde van de chunk-embeddings (uit retrieve), L2-genormaliseerd.
    Mist een document chunk-embeddings, dan deterministisch (her)embedden via de provider."""
    vecs = [c.embedding for c in doc.chunks if c.embedding]
    if vecs:
        dim = len(vecs[0])
        mean = [sum(v[i] for v in vecs) / len(vecs) for i in range(dim)]
        return l2_normalize(mean)
    return l2_normalize(embed.embed([doc.text or doc.source_path])[0])


def _flat_clusters(vectors: list[list[float]], distance: float) -> list[int]:
    """Platte clusters waarbinnen de cofenetische cosinus-afstand ≤ `distance` blijft. Eén document
    → één cluster. `scipy`/`numpy` lazy: alleen deze stage betaalt de import."""
    if len(vectors) == 1:
        return [1]
    import numpy as np
    from scipy.cluster.hierarchy import fcluster, linkage

    linkage_matrix = linkage(np.asarray(vectors, dtype=float), method="average", metric="cosine")
    return [int(c) for c in fcluster(linkage_matrix, t=distance, criterion="distance")]


def _doc_freq(docs: list[Document]) -> Counter:
    """Documentfrequentie per term over de hele kern (voor de TF-IDF-fallbacklabels)."""
    df: Counter = Counter()
    for doc in docs:
        df.update(set(tokenize(doc.text)))
    return df


def _label(cluster_docs, all_docs, providers, audit, df) -> str:
    """Label één cluster: TF-IDF-fallback onder `--no-llm` (geen call), anders één LLM-call."""
    if providers.no_llm:
        return _fallback_label(cluster_docs, len(all_docs), df)
    return _llm_label(cluster_docs, providers.llm, audit)


def _fallback_label(cluster_docs, total: int, df: Counter) -> str:
    """Distinctieve termen: vaak in dit cluster, zeldzaam in de rest. Deterministisch (score↓, term↑)."""
    tf: Counter = Counter()
    for doc in cluster_docs:
        tf.update(set(tokenize(doc.text)))
    scored = []
    for term, count in tf.items():
        if len(term) < 3:
            continue
        idf = math.log(total / (1 + df.get(term, 0)))
        scored.append((count / len(cluster_docs) * idf, term))
    scored.sort(key=lambda s: (-s[0], s[1]))
    terms = [term for _, term in scored[:_LABEL_TERMS]]
    return ", ".join(terms) if terms else "onbenoemd"


def _llm_label(cluster_docs, llm, audit: AuditLog) -> str:
    """Eén LLM-call per cluster: representatieve snippets → kort Nederlands label, prompt gelogd."""
    snippets = "\n".join(f"- {d.text[:200]}" for d in cluster_docs[:5])
    prompt = ("Geef één kort Nederlands onderwerp-label (max 6 woorden) voor deze documenten, "
              "alleen het label:\n" + snippets)
    answer = llm.complete(prompt, system=_SYSTEM)
    label = next((line.strip() for line in answer.splitlines() if line.strip()), "onbenoemd")
    audit.event(STAGE, "label", model=getattr(llm, "name", "?"),
                location=getattr(llm, "location", "?"), prompt=prompt,
                inputs={"label": label, "members": len(cluster_docs)})
    return label
