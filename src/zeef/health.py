"""Extractie-gezondheid — deterministische signalen die de validity-gate consumeert.

Eén keer berekend bij ingest (de loader heeft de ruwe tekst nog), zodat de validity-gate
beslist zónder het bestand opnieuw te openen (design V4). `char_count` + `parse_ok` meten of
er überhaupt iets te beoordelen valt; `redaction_ratio` onderscheidt *leeg* van *gelakt*,
zodat een zwaar-gelakt-maar-relevant document niet als leeg wordt uitgesloten (design V3).
Pure functies: geen I/O, geen LLM, geen netwerk.
"""

from __future__ import annotations

import re

# Metadata-keys op `Document.metadata`. Change #1 raakt `models.py` bewust niet: de
# gezondheid leeft in de vrije metadata-dict (zie coördinatienotitie).
CHAR_COUNT = "char_count"
PARSE_OK = "parse_ok"
REDACTION_RATIO = "redaction_ratio"

# Zwartlak-glyphs die OCR/extractie produceert bij gelakte vlakken.
_REDACTION_GLYPHS = "█▮▯■▆▇"
# Expliciete lak-markeringen in de tekstlaag.
_REDACTION_MARKERS = re.compile(
    r"\[(?:…|\.\.\.|gelakt|zwartgelakt|weggelakt|verwijderd)\]", re.IGNORECASE
)
# Woo-uitzonderingsannotaties (artikelverwijzingen) zoals 5.1.2e, 5.1.1, 10.1, 10.2, 11.1.
# Suffixen expliciet opgesomd i.p.v. `\w?`: dat laatste matchte ook gewone artikelnummers als
# 5.1.10 / 5.1.2a en blies de redaction_ratio op voor niet-gelakte tekst.
_WOO_ANNOTATION = re.compile(r"\b(?:5\.1\.(?:1|2e?|5)|10\.[12]|11\.1)\b")


def redaction_ratio(text: str) -> float:
    """Aandeel redactiesignaal in `text`, geklemd op [0.0, 1.0].

    Telt zwartlak-glyphs, expliciete lak-markeringen en Woo-annotaties als redactie-tekens,
    gedeeld door het aantal niet-witruimte-tekens. Additief en monotoon: meer laksignaal →
    hogere ratio. Bewust grof en goedkoop; de beslis-drempel staat in `config.py` en is
    afstembaar zodra de echte dataset bekend is.
    """
    non_space = sum(1 for c in text if not c.isspace())
    if non_space == 0:
        return 0.0
    glyphs = sum(1 for c in text if c in _REDACTION_GLYPHS)
    marker_chars = sum(len(m.group(0)) for m in _REDACTION_MARKERS.finditer(text))
    woo_chars = sum(len(m.group(0)) for m in _WOO_ANNOTATION.finditer(text))
    signal = glyphs + marker_chars + woo_chars
    return min(1.0, signal / non_space)


def health_metadata(text: str, parse_ok: bool) -> dict:
    """De drie gezondheidsvelden voor `Document.metadata` (zie module-docstring)."""
    return {
        CHAR_COUNT: len(text),
        PARSE_OK: parse_ok,
        REDACTION_RATIO: round(redaction_ratio(text), 4),
    }
