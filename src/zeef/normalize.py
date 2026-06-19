"""Tekstnormalisatie — deterministisch, gedeeld door alle loaders (task 5.4).

De genormaliseerde tekst voedt zowel de content-id (D2) als alle downstream-stages, dus de
normalisatie moet stabiel en formaat-onafhankelijk zijn. Bewust minimaal en voorspelbaar:
regeleindes uniform, witruimte per regel getrimd, overtollige lege regels ingedikt.
"""

from __future__ import annotations

import re

_MULTI_BLANK = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    """Normaliseer ruwe tekst tot een stabiele canonieke vorm.

    - CRLF/CR → LF
    - trailing witruimte per regel verwijderd
    - drie of meer opeenvolgende lege regels → twee
    - omringende witruimte gestript
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    collapsed = _MULTI_BLANK.sub("\n\n", "\n".join(lines))
    return collapsed.strip()
