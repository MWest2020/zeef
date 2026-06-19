"""Kleine, pure-Python vector- en tokenhulp — geen numpy nodig.

Bewust afhankelijkheidsvrij en triviaal te auditen: cosinus en L2-normalisatie op
`list[float]`, plus een deterministische tokenizer die de hele pijplijn deelt. Eén plek
voor deze afleidingen voorkomt dat embed, relate en rerank elk hun eigen variant krijgen.
"""

from __future__ import annotations

import math
import re

_TOKEN_RE = re.compile(r"[0-9a-z]+")


def tokenize(text: str) -> list[str]:
    """Deterministische tokenisatie: lowercase, alfanumerieke runs."""
    return _TOKEN_RE.findall(text.lower())


def l2_normalize(vec: list[float]) -> list[float]:
    """Normaliseer naar lengte 1 (lege/0-vector blijft ongewijzigd)."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosinusgelijkenis van twee even lange vectoren (0.0 bij een nulvector)."""
    if len(a) != len(b):
        raise ValueError(f"vectorlengtes verschillen: {len(a)} != {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
