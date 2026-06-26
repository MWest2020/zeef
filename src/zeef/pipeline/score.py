"""LLM-relevantiescoring (converge-ranking D14/D22/D23 + structured-llm-score): het 'eind'-LLM-touchpoint.

De passage-cosine (`final`, gezet in retrieve) is de selector. Deze stage voegt **alleen een
side-score + motivatie** toe: de top-K kandidaten op `final` gaan naar de LLM, die elk document
scoort tegen de gearticuleerde criteria (0–100 → `llm_relevance`) én een korte motivatie geeft.
De score raakt `final` **niet** aan en demoveert **niemand** (geen recall-gate): `llm_relevance`
en de motivatie zijn transparantie/"why", nooit een filter op wat geselecteerd kan worden.
Onder `--no-llm` slaat de stage volledig over; `final` blijft de cosine voor elke kandidaat.

De score+motivatie worden geparsed in drie tiers (structured-llm-score D-DEGRADE): backends die
`StructuredLLMProvider` vervullen leveren gegarandeerd-parseerbare JSON tegen een vast schema;
anders valt de stage terug op de regex-parse van een vrije-tekst `complete()`; faalt ook die, dan
score-0 met de ruwe tekst. Nooit een crash. De `score`-clamp (0..100 → 0..1) is identiek per pad.
"""

from __future__ import annotations

import re

from zeef.audit import AuditLog
from zeef.models import Criteria, Document
from zeef.profiles import ProviderBundle
from zeef.protocols import StructuredLLMProvider

STAGE = "score"
_SNIPPET = 1500
_SCORE_RE = re.compile(r"score\s*[:=]?\s*(\d{1,3})", re.IGNORECASE)
_MOTIVE_RE = re.compile(r"motivatie\s*[:=]?\s*(.+)", re.IGNORECASE | re.DOTALL)

# Eén vast schema, gedeeld door beide structured-backends (D-SCHEMA).
_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 100},
        "motivatie": {"type": "string"},
    },
    "required": ["score", "motivatie"],
}

_SYSTEM = (
    "Je beoordeelt of een document relevant is voor een Woo-zoekvraag aan de hand van "
    "expliciete criteria. Geef een score van 0 tot 100 en één zin motivatie."
)


def _context(criteria: Criteria, doc: Document) -> str:
    return (
        f"Zoekvraag: {criteria.query}\n\n"
        f"Criteria:\n{criteria.as_prompt_block()}\n\n"
        f"Document ({doc.doc_type}):\n{doc.text[:_SNIPPET]}\n\n"
    )


def _prompt(criteria: Criteria, doc: Document) -> str:
    """Vrije-tekst prompt voor het regex-pad: vraagt expliciet om SCORE:/MOTIVATIE:-regels."""
    return _context(criteria, doc) + (
        "Beoordeel hoe goed dit document aan de criteria voldoet. Geef eerst een regel "
        "'SCORE:' met een getal van 0 tot 100, dan een regel 'MOTIVATIE:' met één zin die "
        "benoemt welke criteria geraakt worden. Bijvoorbeeld:\n"
        "SCORE: 80\n"
        "MOTIVATIE: bevat zowel de publicatie- als de geheimhoudingsclausule tussen de "
        "genoemde partijen"
    )


def _json_prompt(criteria: Criteria, doc: Document) -> str:
    """Prompt voor het structured-pad: het schema dwingt de vorm af, dus geen regel-instructie."""
    return _context(criteria, doc) + (
        "Beoordeel hoe goed dit document aan de criteria voldoet. Geef een score van 0 tot 100 "
        "en één zin motivatie die benoemt welke criteria geraakt worden."
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
        relevance, rationale, route, prompt, raw = _judge(llm, criteria, doc)
        doc.scores["llm_relevance"] = round(relevance, 6)
        doc.rationale = rationale
        inputs: dict = {"relevance": round(relevance, 6), "rationale": rationale[:120], "route": route}
        if route == "structured":
            # D-AUDIT: het JSON-pad logt óók het schema + de ruwe respons, zodat het minstens zo
            # navolgbaar is als de regex-tekst die het vervangt.
            inputs["schema"] = _SCHEMA
            inputs["raw_structured"] = raw
        audit.event(
            STAGE, "llm-score", document_ids=[doc.id],
            model=getattr(llm, "name", "?"), location=getattr(llm, "location", "?"),
            prompt=prompt, inputs=inputs,
        )
    audit.event(STAGE, "score-complete", inputs={
        "query": query, "top_k": top_k, "scored": len(to_score), "candidates": len(candidates),
    })
    return candidates


def _judge(llm, criteria: Criteria, doc: Document) -> tuple[float, str, str, str, dict | None]:
    """Bepaal (relevance, motivatie, route, prompt, raw) voor één document. Structured waar de backend
    het ondersteunt en een geldig object teruggeeft; anders regex-fallback. Werpt nooit door."""
    if isinstance(llm, StructuredLLMProvider):
        prompt = _json_prompt(criteria, doc)
        try:
            raw = llm.complete_json(prompt, _SCHEMA, system=_SYSTEM)
        except Exception:  # noqa: BLE001 — elke backend-fout = val terug op het regex-pad
            raw = None
        parsed = _from_json(raw)
        if parsed is not None:
            return (*parsed, "structured", prompt, raw)
    prompt = _prompt(criteria, doc)
    relevance, rationale = _parse(llm.complete(prompt, system=_SYSTEM))
    return relevance, rationale, "regex", prompt, None


def _from_json(raw: dict | None) -> tuple[float, str] | None:
    """Valideer + normaliseer een structured respons. `None` bij ontbrekende/ongeldige velden →
    de aanroeper valt dan terug op regex. De clamp 0..100 → 0..1 is identiek aan het regex-pad."""
    if not isinstance(raw, dict) or "score" not in raw or "motivatie" not in raw:
        return None
    try:
        relevance = max(0, min(100, int(raw["score"]))) / 100.0
    except (TypeError, ValueError):
        return None
    rationale = str(raw["motivatie"]).strip()[:200] or "geen motivatie uit LLM-antwoord"
    return relevance, rationale


def _parse(answer: str) -> tuple[float, str]:
    """Tolerante regex-parse: SCORE 0-100 → 0..1, MOTIVATIE → zin. Onparseerbaar → 0 + ruwe tekst."""
    score_match = _SCORE_RE.search(answer)
    motive_match = _MOTIVE_RE.search(answer)
    if score_match is None:
        return 0.0, answer.strip()[:200] or "geen score uit LLM-antwoord"
    relevance = max(0, min(100, int(score_match.group(1)))) / 100.0
    rationale = motive_match.group(1).strip() if motive_match else answer.strip()[:200]
    return relevance, rationale
