"""Scope-filter-stage (scope-filter-spec): regels eerst, LLM alleen voor de rest.

De geordende regelset (`scope_rules.RULES`) beslist deterministisch en goedkoop. Alleen
documenten die geen enkele regel beslist gaan naar de LLM, en alleen als er een LLM-provider
is (niet onder `--no-llm`). Elke beslissing — regel of LLM — krijgt een `decision_reason` en
een audit-event; LLM-events bevatten de exacte prompt, het model en de locatie.
"""

from __future__ import annotations

from zeef.audit import AuditLog
from zeef.models import Document
from zeef.pipeline.scope_rules import RULES
from zeef.profiles import ProviderBundle

STAGE = "scope-filter"

_LLM_SYSTEM = (
    "Je bent een hulp bij een Woo-verzoek. Bepaal of een document relevant kan zijn voor de "
    "zoekvraag. Antwoord met exact één woord: RELEVANT of NIET-RELEVANT."
)


def _llm_prompt(query: str, doc: Document) -> str:
    snippet = doc.text[:1500]
    return (
        f"Zoekvraag: {query}\n\n"
        f"Document ({doc.doc_type}):\n{snippet}\n\n"
        "Kan dit document relevant zijn voor de zoekvraag? Antwoord RELEVANT of NIET-RELEVANT."
    )


def scope_filter(
    docs: list[Document], providers: ProviderBundle, audit: AuditLog, query: str
) -> list[Document]:
    """Markeer out-of-scope documenten; laat de rest `undecided` voor retrieval."""
    residue: list[Document] = []
    for doc in docs:
        reason = _apply_rules(doc)
        if reason is not None:
            doc.decision = "out_of_scope"
            doc.decision_reason = reason
            audit.event(STAGE, "excluded", document_ids=[doc.id], inputs={"reason": reason})
        else:
            residue.append(doc)
    _llm_fallback(residue, providers, audit, query)
    audit.event(STAGE, "scope-complete", inputs={
        "excluded": sum(1 for d in docs if d.decision == "out_of_scope"),
        "undecided": sum(1 for d in docs if d.decision == "undecided"),
        "no_llm": providers.no_llm,
    })
    return docs


def _apply_rules(doc: Document) -> str | None:
    if doc.decision == "out_of_scope":
        return doc.decision_reason or None
    for _name, rule in RULES:
        reason = rule(doc)
        if reason is not None:
            return reason
    return None


def _llm_fallback(
    residue: list[Document], providers: ProviderBundle, audit: AuditLog, query: str
) -> None:
    if providers.no_llm:
        if residue:
            audit.event(STAGE, "llm-skipped", document_ids=[d.id for d in residue],
                        inputs={"reason": "--no-llm: twijfelgevallen blijven undecided"})
        return
    llm = providers.llm
    for doc in residue:
        prompt = _llm_prompt(query, doc)
        verdict = llm.complete(prompt, system=_LLM_SYSTEM)
        out_of_scope = "niet-relevant" in verdict.strip().lower()
        audit.event(
            STAGE, "llm-decision", document_ids=[doc.id],
            model=getattr(llm, "name", "?"), location=getattr(llm, "location", "?"),
            prompt=prompt, inputs={"verdict": verdict.strip()[:80]},
        )
        if out_of_scope:
            doc.decision = "out_of_scope"
            doc.decision_reason = f"LLM-oordeel NIET-RELEVANT voor zoekvraag (model {getattr(llm, 'name', '?')})"
