"""Validity-gate — deterministische pre-flight vóór de relevantiefase (validity-gate-spec).

Beantwoordt één vraag per document: *is dit überhaupt te beoordelen?* — nooit *is het
relevant?*. Sluit mechanisch-onbruikbare documenten uit (mislukte parse, leeg-na-OCR) met een
machine-onderscheidbare `validity:`-reden, en behoudt zwaar-gelakte-maar-leesbare documenten
(design V3). Volledig deterministisch: geen LLM, identiek onder `--no-llm` en air-gapped.

Niet hier: exacte/near-duplicaten — die worden al deterministisch afgehandeld in relate +
scope-filter (`rule_duplicate`); de gate dupliceert dat pad niet (design V2).
"""

from __future__ import annotations

from zeef.audit import AuditLog
from zeef.health import CHAR_COUNT, PARSE_OK, REDACTION_RATIO
from zeef.models import Document

try:  # optionele taaldetectie; één keer geprobeerd bij import, niet per document
    from langdetect import detect as _detect  # type: ignore
except ImportError:  # pragma: no cover - langdetect is optioneel
    _detect = None

STAGE = "validity"

# Markering op een behouden, vermoedelijk gelakt document (zacht; verandert de selectie niet).
REDACTION_NOTE = "verminderd leesbaar (vermoedelijk gelakt)"
# Metadata-key die de "vermoedelijk gelakt"-status *canoniek* en duurzaam draagt. `decision_reason`
# krijgt dezelfde markering bij de gate, maar is vluchtig: select() en scope-filter overschrijven
# `decision_reason` downstream. Wie de gelakt-status leest (inventory/export, viewer) moet daarom
# `metadata["redaction_note"]` gebruiken, niet `decision_reason`.
REDACTION_META_KEY = "redaction_note"


def validity_gate(
    docs: list[Document],
    audit: AuditLog,
    *,
    min_chars: int,
    redaction_ratio_threshold: float,
) -> list[Document]:
    """Sluit onbruikbare documenten uit, behoud gelakt-maar-leesbare; geef `docs` terug.

    Leest de bij ingest vastgelegde gezondheidsmetadata; opent geen bestand opnieuw. Ontbreekt
    een veld (bv. een loader die het niet zet), dan geldt de bruikbare-default: `parse_ok=True`,
    `char_count=len(text)`, `redaction_ratio=0.0`.
    """
    excluded = 0
    redacted_kept = 0
    for doc in docs:
        if not doc.metadata.get(PARSE_OK, True):
            _exclude(doc, audit, "corrupt-pdf", "PDF kon niet worden geparsed")
            excluded += 1
            continue
        char_count = int(doc.metadata.get(CHAR_COUNT, len(doc.text)))
        if char_count < min_chars:
            ratio = float(doc.metadata.get(REDACTION_RATIO, 0.0))
            if ratio >= redaction_ratio_threshold:
                _keep_redacted(doc, audit, char_count, ratio)
                redacted_kept += 1
                continue
            _exclude(doc, audit, "empty-after-ocr",
                     f"te weinig leesbare tekst ({char_count} tekens, geen laksignaal)")
            excluded += 1
            continue
        _language_signal(doc, audit)
    audit.event(STAGE, "validity-complete", inputs={
        "documents": len(docs), "excluded": excluded, "redacted_kept": redacted_kept,
        "min_chars": min_chars, "redaction_ratio_threshold": redaction_ratio_threshold,
    })
    return docs


def _exclude(doc: Document, audit: AuditLog, check: str, detail: str) -> None:
    """Markeer onbruikbaar als out_of_scope met een `validity:`-reden + audit-event."""
    reason = f"validity:{check}"
    doc.decision = "out_of_scope"
    doc.decision_reason = reason
    # action="excluded" + inputs.reason: zelfde vorm als scope-filter, zodat de audit-eis
    # "elk uitgesloten document draagt een reden" uniform geldt.
    audit.event(STAGE, "excluded", document_ids=[doc.id],
                inputs={"reason": reason, "check": check, "detail": detail})


def _keep_redacted(doc: Document, audit: AuditLog, char_count: int, ratio: float) -> None:
    """Behoud een vermoedelijk gelakt document; markeer het, sluit het niet uit (design V3)."""
    # `redaction_note` is de duurzame, canonieke markering; `decision_reason` is een vluchtige
    # echo (overschreven door select()/scope-filter) — zie REDACTION_META_KEY.
    doc.metadata[REDACTION_META_KEY] = REDACTION_NOTE
    doc.decision_reason = REDACTION_NOTE  # blijft `undecided`; gaat door naar retrieve/score
    audit.event(STAGE, "redaction-kept", document_ids=[doc.id],
                inputs={"char_count": char_count, "redaction_ratio": ratio,
                        "note": REDACTION_NOTE})


def _language_signal(doc: Document, audit: AuditLog) -> None:
    """Zacht taalsignaal: nooit een uitsluiting, nooit een crash (design V2/risks).

    Detecteert de taal alleen als een optionele detector aanwezig is; ontbreekt die, dan
    'taal onbekend'. Puur informatief in de audit-log.
    """
    if _detect is None or not doc.text.strip():
        return  # detector afwezig of geen tekst → 'taal onbekend' (zacht), geen event
    try:
        lang = _detect(doc.text)
    except Exception:  # noqa: BLE001 — detector onzeker op deze tekst → zacht overslaan
        return
    audit.event(STAGE, "language", document_ids=[doc.id], inputs={"language": lang})
