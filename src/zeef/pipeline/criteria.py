"""Criteria-articulatie (criteria-spec, design.md D9/D10): het 'begin'-LLM-touchpoint.

Eén LLM-call vertaalt de verfijnde zoekvraag naar een korte, expliciete set benoemde
relevantiecriteria — de geschreven relevantiedefinitie die een beoordelaar kan lezen én
betwisten. Onder `--no-llm` valt de stage deterministisch terug op één criterium gelijk aan
de ruwe zoekvraag, zodat de pijplijn air-gapped blijft draaien. De gearticuleerde criteria
gaan zowel naar de audit-log (mét de exacte prompt) als naar het `criteria.json`-artefact.
"""

from __future__ import annotations

from zeef.audit import AuditLog
from zeef.models import Criteria, Criterion
from zeef.profiles import ProviderBundle

STAGE = "criteria"

_SYSTEM = (
    "Je bent een hulp bij een Woo-verzoek (Wet open overheid). Leid uit een verfijnde "
    "zoekvraag een korte set expliciete relevantiecriteria af waarmee documenten te "
    "beoordelen zijn."
)


def _prompt(query: str) -> str:
    return (
        f"Zoekvraag: {query}\n\n"
        "Welke kenmerken maken een document relevant voor deze zoekvraag? Geef 3 tot 6 "
        "criteria, elk op een eigen regel als 'kernwoord: korte omschrijving'. Bijvoorbeeld:\n"
        "geheimhouding: het document bevat een geheimhoudingsclausule\n"
        "betrokken partijen: de in de zoekvraag genoemde partijen komen voor\n\n"
        "Geef alleen de criteria, zonder inleiding, opsomtekens of nummering."
    )


def articulate_criteria(query: str, providers: ProviderBundle, audit: AuditLog) -> Criteria:
    """Leid de relevantiecriteria af uit `query`; deterministische terugval onder `--no-llm`."""
    if providers.no_llm:
        criteria = _fallback(query)
        audit.event(STAGE, "fallback", inputs={
            "reason": "--no-llm: criteria = ruwe zoekvraag", "query": query,
        })
        return criteria

    llm = providers.llm
    prompt = _prompt(query)
    answer = llm.complete(prompt, system=_SYSTEM)
    items = _parse(answer)
    criteria = Criteria(query=query, items=items, source="llm") if items else _fallback(query)
    audit.event(
        STAGE, "articulate",
        model=getattr(llm, "name", "?"), location=getattr(llm, "location", "?"),
        prompt=prompt, inputs={
            "query": query, "source": criteria.source,
            "criteria": [c.label for c in criteria.items],
        },
    )
    return criteria


def _parse(answer: str) -> list[Criterion]:
    """Tolerante regel-parse: 'LABEL: omschrijving'; lege/colon-loze regels worden overgeslagen."""
    items: list[Criterion] = []
    for raw in answer.splitlines():
        line = raw.strip().lstrip("-*0123456789. ").strip()
        if ":" not in line:
            continue
        label, _, description = line.partition(":")
        label, description = label.strip(), description.strip()
        if label and description:
            items.append(Criterion(label=label, description=description))
    return items


def _fallback(query: str) -> Criteria:
    """Eén deterministisch criterium gelijk aan de ruwe zoekvraag."""
    item = Criterion(label="zoekvraag", description=query)
    return Criteria(query=query, items=[item], source="fallback")
