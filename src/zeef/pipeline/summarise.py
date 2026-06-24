"""Per-document inhoudssamenvatting (summarise-spec): ≤N woorden, LLM, ná select + topics.

Eén LLM-call per geselecteerd document levert een korte samenvatting van *wat* het document zegt —
nadrukkelijk los van de `rationale` (waaróm het scoort). Onder `--no-llm` slaat de stage volledig
over: geen samenvatting, geen model-call (de export laat de `summary`-kolom dan weg). De exacte
prompt, het model en de locatie gaan naar de audit-log; temperatuur-0 regelt de driver.
"""

from __future__ import annotations

from zeef.audit import AuditLog
from zeef.models import Document
from zeef.profiles import ProviderBundle

STAGE = "summarise"
DEFAULT_SUMMARY_MAX_WORDS = 100
_SNIPPET = 2000
_CLUSTER_REPS = 4  # representatieve leden (medoid-eerst) die de cluster-samenvatting voeden
_SYSTEM = ("Je vat een overheidsdocument bondig samen in het Nederlands. Beschrijf uitsluitend de "
           "inhoud — niet of het relevant is.")
_CLUSTER_SYSTEM = ("Je benoemt bondig in het Nederlands het gemeenschappelijke onderwerp van een "
                   "groep documenten. Beschrijf waar de groep over gaat, geen oordeel.")


def summarise(
    selected: list[Document],
    providers: ProviderBundle,
    audit: AuditLog,
    *,
    max_words: int = DEFAULT_SUMMARY_MAX_WORDS,
) -> None:
    """Zet `metadata["summary"]` per geselecteerd document. Skip (zonder call) onder `--no-llm`."""
    if providers.no_llm or not selected:
        audit.event(STAGE, "skipped", inputs={
            "reason": "--no-llm: geen samenvatting" if providers.no_llm else "geen selectie",
            "selected": len(selected),
        })
        return
    llm = providers.llm
    for doc in selected:
        prompt = _prompt(doc, max_words)
        answer = llm.complete(prompt, system=_SYSTEM)
        summary = _truncate_words(answer.strip(), max_words)
        doc.metadata["summary"] = summary
        audit.event(STAGE, "summary", document_ids=[doc.id],
                    model=getattr(llm, "name", "?"), location=getattr(llm, "location", "?"),
                    prompt=prompt, inputs={"words": len(summary.split())})
    audit.event(STAGE, "summarise-complete",
                inputs={"summarised": len(selected), "max_words": max_words})


def summarise_cluster(members: list[Document], providers: ProviderBundle, audit: AuditLog,
                      *, max_words: int = DEFAULT_SUMMARY_MAX_WORDS) -> str:
    """Eén samenvatting per cluster (discover): wáár gaat deze groep over, op basis van de
    representatieve leden (medoid-eerst aangeleverd) — niet één call per document. Onder `--no-llm`
    geen samenvatting en geen model-call. Prompt/model/locatie gaan naar de audit-log."""
    if providers.no_llm or not members:
        return ""
    llm = providers.llm
    reps = members[:_CLUSTER_REPS]
    body = "\n\n".join(f"- {d.text[:_SNIPPET // _CLUSTER_REPS]}" for d in reps)
    prompt = (f"Vat in maximaal {max_words} woorden samen waar deze groep documenten gezamenlijk "
              f"over gaat (het gemeenschappelijke onderwerp), in het Nederlands.\n\n{body}")
    summary = _truncate_words(llm.complete(prompt, system=_CLUSTER_SYSTEM).strip(), max_words)
    audit.event(STAGE, "cluster-summary", document_ids=[d.id for d in reps],
                model=getattr(llm, "name", "?"), location=getattr(llm, "location", "?"),
                prompt=prompt, inputs={"members": len(members), "words": len(summary.split())})
    return summary


def _prompt(doc: Document, max_words: int) -> str:
    return (
        f"Vat de inhoud van dit document samen in maximaal {max_words} woorden. Beschrijf WÁT het "
        f"document zegt (onderwerp, kern, betrokkenen), niet of het relevant is.\n\n"
        f"Document ({doc.doc_type}):\n{doc.text[:_SNIPPET]}"
    )


def _truncate_words(text: str, max_words: int) -> str:
    """Harde woordlimiet als terugval — de prompt vraagt al om ≤`max_words`."""
    words = text.split()
    return text if len(words) <= max_words else " ".join(words[:max_words])
