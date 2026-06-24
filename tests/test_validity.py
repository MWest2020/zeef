"""Validity-gate (validity-gate-spec): mechanisch-onbruikbaar uit, gelakt behouden, geen LLM.

De gate werkt op de bij ingest vastgelegde gezondheidsmetadata, dus de tests construeren
`Document`s met die metadata direct — deterministisch en zonder echte PDF's nodig.
"""

import json

from zeef.health import REDACTION_RATIO, health_metadata, redaction_ratio
from zeef.models import Document
from zeef.pipeline.retrieve import candidates_of
from zeef.pipeline.validity import REDACTION_NOTE, validity_gate

MIN_CHARS = 50
THRESHOLD = 0.10


def _events(audit):
    return [json.loads(line) for line in audit.path.read_text(encoding="utf-8").splitlines()]


def _validity_excluded(docs):
    """Spiegelt de telpredikaat uit RunResult.counts: out_of_scope met een `validity:`-reden."""
    return [d for d in docs
            if d.decision == "out_of_scope" and d.decision_reason.startswith("validity:")]


def _doc(doc_id, text, *, parse_ok=True, redaction=None):
    meta = health_metadata(text, parse_ok)
    if redaction is not None:  # overschrijf de gemeten ratio voor een gericht scenario
        meta[REDACTION_RATIO] = redaction
    return Document(id=doc_id, source_path=f"/{doc_id}.pdf", doc_type="pdf_digital",
                    metadata=meta, text=text)


def _gate(docs, audit):
    return validity_gate(docs, audit, min_chars=MIN_CHARS, redaction_ratio_threshold=THRESHOLD)


def test_unparseable_pdf_excluded_with_reason(audit):
    doc = _doc("corrupt", "", parse_ok=False)
    _gate([doc], audit)
    assert doc.decision == "out_of_scope"
    assert doc.decision_reason == "validity:corrupt-pdf"
    excluded = [e for e in _events(audit) if e["action"] == "excluded"]
    assert excluded and excluded[0]["document_ids"] == ["corrupt"]
    assert excluded[0]["inputs"]["check"] == "corrupt-pdf"


def test_empty_after_ocr_excluded(audit):
    doc = _doc("leeg", "   \n  ")  # vrijwel geen tekst, geen laksignaal
    _gate([doc], audit)
    assert doc.decision == "out_of_scope"
    assert doc.decision_reason == "validity:empty-after-ocr"


def test_redacted_low_text_is_kept_not_excluded(audit):
    # Weinig tekst, maar duidelijk laksignaal → behouden, gemarkeerd, blijft undecided.
    doc = _doc("gelakt", "Betreft: [gelakt] 5.1.2e\n█████ 5.1.2e")
    assert doc.metadata[REDACTION_RATIO] >= THRESHOLD  # de heuristiek herkent het lakken
    _gate([doc], audit)
    assert doc.decision == "undecided"
    assert doc.decision_reason == REDACTION_NOTE
    assert doc.metadata["redaction_note"] == REDACTION_NOTE
    kept = [e for e in _events(audit) if e["action"] == "redaction-kept"]
    assert kept and kept[0]["document_ids"] == ["gelakt"]


def test_redacted_document_survives_the_gate(audit):
    """De gevaarlijke spiegelkant: een zwaar gelakt, relevant-ogend document mág niet als
    leeg worden uitgesloten. Het moet de gate overleven en eligible blijven voor scoring —
    een valse uitsluiting hier kost recall op precies een gelakt-maar-relevant document.
    """
    # Weinig tekst (onder min_chars) maar onmiskenbaar laksignaal: glyphs + [gelakt] + [...]
    # + een Woo-annotatie. Echt signaal, geen geforceerde ratio.
    text = "Betreft: [gelakt]\n█████ 5.1.2e\n[…]"
    doc = _doc("gelakt-relevant", text)
    assert len(text) < MIN_CHARS  # zit echt onder de leeg-drempel
    assert doc.metadata[REDACTION_RATIO] >= THRESHOLD  # heuristiek herkent het lakken

    _gate([doc], audit)

    # 1. niet uitgesloten
    assert doc.decision != "out_of_scope"
    # 2. blijft undecided (gaat de relevantiefase in)
    assert doc.decision == "undecided"
    # 3. gemarkeerd als verminderd leesbaar / vermoedelijk gelakt
    assert doc.decision_reason == REDACTION_NOTE
    assert "gelakt" in doc.decision_reason
    assert doc.metadata["redaction_note"] == REDACTION_NOTE
    # 4. dus eligible voor retrieve/score, en níét in de validity-uitgesloten telling
    assert doc in candidates_of([doc])
    assert _validity_excluded([doc]) == []
    # En geen empty-after-ocr-uitsluiting in de audit voor dit document.
    excluded = [e for e in _events(audit) if e["action"] == "excluded"]
    assert not excluded


def test_redaction_ratio_is_the_differentiator(audit):
    """Grens-test: bij gelijke (lage) tekstlengte beslist alléén de redaction_ratio.

    Eén document net ónder de drempel → empty-after-ocr (uitsluiten); één net erboven →
    behouden. Bewijst dat het de redaction_ratio is die het onderscheid maakt, niet de
    tekstlengte (die is identiek).
    """
    short_text = "weinig leesbare tekst"  # zelfde lengte voor beide; ruim onder min_chars
    assert len(short_text) < MIN_CHARS
    below = _doc("net-onder", short_text, redaction=THRESHOLD - 0.01)
    above = _doc("net-boven", short_text, redaction=THRESHOLD + 0.01)
    assert below.metadata[REDACTION_RATIO] < THRESHOLD <= above.metadata[REDACTION_RATIO]
    # Gelijke tekstlengte → de enige variabele is de redaction_ratio.
    assert below.metadata["char_count"] == above.metadata["char_count"]

    _gate([below, above], audit)

    # Net onder de drempel: geen laksignaal genoeg → leeg-na-OCR uitgesloten.
    assert below.decision == "out_of_scope"
    assert below.decision_reason == "validity:empty-after-ocr"
    # Net erboven: vermoedelijk gelakt → behouden, undecided, gemarkeerd.
    assert above.decision == "undecided"
    assert above.decision_reason == REDACTION_NOTE
    # Telling: precies één validity-uitsluiting, en dat is het document zónder genoeg signaal.
    assert _validity_excluded([below, above]) == [below]


def test_usable_documents_pass_unchanged(audit):
    text = "Dit is een normaal, leesbaar beleidsdocument over de begroting 2026. " * 3
    docs = [_doc("a", text), _doc("b", text + " extra")]
    _gate(docs, audit)
    assert all(d.decision == "undecided" for d in docs)
    # Geen enkele uitsluiting wanneer alles bruikbaar is (recall ongewijzigd).
    assert not [e for e in _events(audit) if e["action"] == "excluded"]


def test_validity_makes_no_llm_call(audit):
    # De gate krijgt geen provider; ze mag er ook geen nodig hebben (volledig deterministisch).
    doc = _doc("x", "")
    _gate([doc], audit)
    assert not [e for e in _events(audit) if e.get("action") == "llm-decision"]


def test_missing_health_metadata_defaults_to_usable(audit):
    # Een document zonder gezondheidsmetadata (andere loader) mag niet vals worden uitgesloten.
    long_text = "inhoudelijk document met voldoende tekst om beoordeeld te worden. " * 2
    doc = Document(id="geen-meta", source_path="/x.eml", doc_type="email", text=long_text)
    _gate([doc], audit)
    assert doc.decision == "undecided"


def test_redaction_ratio_is_zero_for_clean_text():
    assert redaction_ratio("Gewoon een nette zin zonder enige redactie.") == 0.0
    assert redaction_ratio("") == 0.0
    assert redaction_ratio("█████ [gelakt] 5.1.2e") > 0.0
