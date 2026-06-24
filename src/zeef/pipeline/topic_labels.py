"""Topic-labelling (topic-clustering-spec): kort label per cluster — LLM of deterministisch TF-IDF.

Gescheiden van de clustering (`topics.py`) zodat elk bestand één verantwoordelijkheid heeft en
onder de 200-regelgrens blijft. Onder `--no-llm` worden labels uit distinctieve termen gebouwd
(cluster vs. de rest), zónder enige model-call. Anders levert één LLM-call per cluster een kort
Nederlands label op, met de exacte prompt, het model en de locatie in de audit-log. De aanroeper
levert de clusterleden medoid-eerst aan, zodat de snippets representatief zijn (medoid + naaste
leden).
"""

from __future__ import annotations

import math
from collections import Counter

from zeef.audit import AuditLog
from zeef.models import Document
from zeef.profiles import ProviderBundle
from zeef.similarity import tokenize

STAGE = "topics"
_LABEL_TERMS = 3
_SNIPPETS = 5
_SYSTEM = "Je benoemt een groep documenten met één kort, concreet Nederlands onderwerp-label."


def doc_freq(docs: list[Document]) -> Counter:
    """Documentfrequentie per term over de hele kern (noemer voor de TF-IDF-fallbacklabels)."""
    df: Counter = Counter()
    for doc in docs:
        df.update(set(tokenize(doc.text)))
    return df


def label_cluster(
    members: list[Document],
    total: int,
    providers: ProviderBundle,
    audit: AuditLog,
    df: Counter | None,
) -> str:
    """Label één cluster. `members` staat medoid-eerst. Onder `--no-llm`: TF-IDF, geen model-call."""
    if providers.no_llm:
        return _fallback_label(members, total, df or Counter())
    return _llm_label(members, providers.llm, audit)


def _fallback_label(members: list[Document], total: int, df: Counter) -> str:
    """Distinctieve termen: vaak in dit cluster, zeldzaam in de rest. Deterministisch (score↓, term↑)."""
    tf: Counter = Counter()
    for doc in members:
        tf.update(set(tokenize(doc.text)))
    scored = []
    for term, count in tf.items():
        if len(term) < 3:
            continue
        idf = math.log(total / (1 + df.get(term, 0)))
        scored.append((count / len(members) * idf, term))
    scored.sort(key=lambda s: (-s[0], s[1]))
    terms = [term for _, term in scored[:_LABEL_TERMS]]
    return ", ".join(terms) if terms else "onbenoemd"


def _snippet(doc: Document) -> str:
    """Titel (indien bekend) + eerste regels van de tekst, op één regel samengevat."""
    title = str(doc.metadata.get("title", "")).strip()
    head = " ".join(doc.text.split())[:200]
    return f"{title} — {head}" if title else head


def _llm_label(members: list[Document], llm, audit: AuditLog) -> str:
    """Eén LLM-call: representatieve snippets (medoid + naaste leden) → kort label; prompt gelogd."""
    body = "\n".join(f"- {_snippet(doc)}" for doc in members[:_SNIPPETS])
    prompt = ("Geef precies één kort Nederlands onderwerp-label (max 6 woorden) voor deze "
              "documenten. Antwoord met alléén het label, zonder toelichting.\n\n" + body)
    answer = llm.complete(prompt, system=_SYSTEM)
    label = next((line.strip() for line in answer.splitlines() if line.strip()), "onbenoemd")
    audit.event(STAGE, "label", model=getattr(llm, "name", "?"),
                location=getattr(llm, "location", "?"), prompt=prompt,
                inputs={"label": label, "members": len(members)})
    return label
