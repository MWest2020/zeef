"""LLM-relevantiescoring (retrieve-rerank-spec, converge-ranking D14/D22/D23): het 'eind'-LLM-touchpoint.

De passage-cosine (`final`, gezet in retrieve) is de selector. Deze stage voegt **alleen een
side-score + motivatie** toe: de top-K kandidaten op `final` gaan naar de LLM, die elk document
scoort tegen de gearticuleerde criteria (0–100 → `llm_relevance`) én een korte motivatie geeft.
De score raakt `final` **niet** aan en demoveert **niemand** (geen recall-gate): `llm_relevance`
en de motivatie zijn transparantie/"why", nooit een filter op wat geselecteerd kan worden.
Onder `--no-llm` slaat de stage volledig over; `final` blijft de cosine voor elke kandidaat.
"""

from __future__ import annotations

import re

from zeef.audit import AuditLog
from zeef.models import Criteria, Document
from zeef.profiles import ProviderBundle

STAGE = "score"
_SNIPPET = 1500
_SCORE_RE = re.compile(r"score\s*[:=]?\s*(\d{1,3})", re.IGNORECASE)
_MOTIVE_RE = re.compile(r"motivatie\s*[:=]?\s*(.+)", re.IGNORECASE | re.DOTALL)

_SYSTEM = (
    "Je beoordeelt of een document relevant is voor een Woo-zoekvraag aan de hand van "
    "expliciete criteria. Geef een score van 0 tot 100 en één zin motivatie."
)


def _prompt(criteria: Criteria, doc: Document) -> str:
    return (
        f"Zoekvraag: {criteria.query}\n\n"
        f"Criteria:\n{criteria.as_prompt_block()}\n\n"
        f"Document ({doc.doc_type}):\n{doc.text[:_SNIPPET]}\n\n"
        "Beoordeel hoe goed dit document aan de criteria voldoet. Geef eerst een regel "
        "'SCORE:' met een getal van 0 tot 100, dan een regel 'MOTIVATIE:' met één zin die "
        "benoemt welke criteria geraakt worden. Bijvoorbeeld:\n"
        "SCORE: 80\n"
        "MOTIVATIE: bevat zowel de publicatie- als de geheimhoudingsclausule tussen de "
        "genoemde partijen"
    )


def score(
    candidates: list[Document], criteria: Criteria, providers: ProviderBundle,
    audit: AuditLog, query: str, *, top_k: int = 0,
) -> list[Document]:
    """Scoor de top-K kandidaten (op `final`/cosine) met de LLM als side-score + motivatie. Geen
    demotion, `final` blijft de cosine. Skip onder `--no-llm`."""
    if providers.no_llm or not candidates:
        audit.event(STAGE, "skipped", inputs={
            "reason": "--no-llm: final blijft de passage-cosine" if providers.no_llm
            else "geen kandidaten",
            "candidates": len(candidates),
        })
        return candidates

    # Kies de top-K op de cosine-selector (`final`), niet op de rerank-volgorde: we lichten de
    # meest relevante kandidaten toe met een motivatie. Tie-break op id voor determinisme.
    ordered = sorted(candidates, key=lambda d: (-d.scores.get("final", 0.0), d.id))
    to_score = ordered if top_k <= 0 else ordered[:top_k]
    llm = providers.llm
    for doc in to_score:
        prompt = _prompt(criteria, doc)
        answer = llm.complete(prompt, system=_SYSTEM)
        relevance, rationale = _parse(answer)
        doc.scores["llm_relevance"] = round(relevance, 6)
        doc.rationale = rationale
        audit.event(
            STAGE, "llm-score", document_ids=[doc.id],
            model=getattr(llm, "name", "?"), location=getattr(llm, "location", "?"),
            prompt=prompt, inputs={"relevance": round(relevance, 6), "rationale": rationale[:120]},
        )
    audit.event(STAGE, "score-complete", inputs={
        "query": query, "top_k": top_k, "scored": len(to_score), "candidates": len(candidates),
    })
    return candidates


def _parse(answer: str) -> tuple[float, str]:
    """Tolerante parse: SCORE 0-100 → 0..1, MOTIVATIE → zin. Onparseerbaar → 0 + ruwe tekst."""
    score_match = _SCORE_RE.search(answer)
    motive_match = _MOTIVE_RE.search(answer)
    if score_match is None:
        return 0.0, answer.strip()[:200] or "geen score uit LLM-antwoord"
    relevance = max(0, min(100, int(score_match.group(1)))) / 100.0
    rationale = motive_match.group(1).strip() if motive_match else answer.strip()[:200]
    return relevance, rationale
