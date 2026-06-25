"""Scope-filter-stage (scope-filter-spec): regels eerst, LLM alleen voor de rest.

De geordende regelset (`scope_rules.RULES`) beslist deterministisch en goedkoop. Alleen
documenten die geen enkele regel beslist gaan naar de LLM, en alleen als er een LLM-provider
is (niet onder `--no-llm`). De LLM-stap is **recall-georiënteerd**: hij sluit alleen uit wat met
zekerheid buiten scope valt en behoudt twijfelgevallen (de precisie-verfijning gebeurt later in
de relevantiescoring). Elke beslissing — regel of LLM — krijgt een `decision_reason` en een
audit-event; LLM-events bevatten de exacte prompt, het model en de locatie.
"""

from __future__ import annotations

from zeef.audit import AuditLog
from zeef.models import Document
from zeef.pipeline.scope_rules import RULES
from zeef.profiles import ProviderBundle

STAGE = "scope-filter"

_LLM_SYSTEM = (
    "Je bent een hulp bij een Woo-verzoek. Recall gaat vóór precisie: sluit een document "
    "alléén uit als het met zekerheid buiten de zoekvraag valt; bij enige twijfel behoud je het "
    "(de verfijning gebeurt later in de relevantiescoring). Antwoord met exact één woord: "
    "UITSLUITEN of BEHOUDEN."
)


def _llm_prompt(query: str, doc: Document) -> str:
    snippet = doc.text[:1500]
    return (
        f"Zoekvraag: {query}\n\n"
        f"Document ({doc.doc_type}):\n{snippet}\n\n"
        "Valt dit document met zekerheid buiten de zoekvraag? Antwoord UITSLUITEN alleen als het "
        "duidelijk een ander onderwerp betreft; bij twijfel BEHOUDEN."
    )


def _is_exclude_verdict(verdict: str) -> bool:
    """Recall-veilig: alleen uitsluiten als het eerste woord 'uitsluiten' is (anders behouden)."""
    tokens = verdict.strip().lower().split()
    return bool(tokens) and tokens[0].startswith("uitsluiten")


def scope_filter(
    docs: list[Document], providers: ProviderBundle, audit: AuditLog, query: str,
    *, scope_llm: bool = True,
) -> list[Document]:
    """Markeer out-of-scope documenten; laat de rest `undecided` voor retrieval.

    `scope_llm=False` zet de per-doc LLM-poort uit: alleen de deterministische `RULES` beslissen
    reikwijdte, de twijfelgevallen blijven `undecided` en stromen naar de selector. Reikwijdte
    wordt zo zuiver procesrol (regels), relevantie blijft de selector — de LLM velt geen
    reikwijdte-oordeel meer.
    """
    residue: list[Document] = []
    for doc in docs:
        reason = _apply_rules(doc)
        if reason is not None:
            doc.decision = "out_of_scope"
            doc.decision_reason = reason
            audit.event(STAGE, "excluded", document_ids=[doc.id], inputs={"reason": reason})
        else:
            residue.append(doc)
    if scope_llm:
        _llm_fallback(residue, providers, audit, query)
    elif residue:
        audit.event(STAGE, "llm-gate-off", document_ids=[d.id for d in residue],
                    inputs={"reason": "scope_filter_llm=off: alleen regels; twijfel → undecided",
                            "residue": len(residue)})
    audit.event(STAGE, "scope-complete", inputs={
        "excluded": sum(1 for d in docs if d.decision == "out_of_scope"),
        "undecided": sum(1 for d in docs if d.decision == "undecided"),
        "no_llm": providers.no_llm, "scope_llm": scope_llm,
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
        out_of_scope = _is_exclude_verdict(verdict)
        audit.event(
            STAGE, "llm-decision", document_ids=[doc.id],
            model=getattr(llm, "name", "?"), location=getattr(llm, "location", "?"),
            prompt=prompt, inputs={"verdict": verdict.strip()[:80]},
        )
        if out_of_scope:
            doc.decision = "out_of_scope"
            doc.decision_reason = f"LLM-oordeel: met zekerheid buiten scope (UITSLUITEN, model {getattr(llm, 'name', '?')})"
