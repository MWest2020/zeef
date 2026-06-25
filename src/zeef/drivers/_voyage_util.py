"""Pure helpers voor de Voyage-drivers: token-schatting, truncatie, batching.

Apart van `drivers/voyage.py` gehouden zodat die module ruimte houdt voor de HTTP-/retry-logica
en onder de 200-regellimiet blijft. Geen netwerk, geen state — puur functioneel en los testbaar.
"""

from __future__ import annotations

# Conservatieve token-schatting (Voyage ~3-4 tekens/token NL): delen door 3 overschat tokens, dus
# de grens grijpt vroeger in (veilig) i.p.v. een echte 400 te riskeren.
_CHARS_PER_TOKEN_EST = 3


def _truncate(texts: list[str], max_chars: int) -> tuple[list[str], int, int]:
    """Kap elke tekst op `max_chars` (≤0 = uit). Geeft (gekapte_lijst, aantal_gekapt, max_orig_len).

    Truncatie is deterministisch (eerste `max_chars` tekens) en client-side, zodat de toegepaste
    grens reproduceerbaar en auditbaar is i.p.v. server-side stil afgekapt.
    """
    max_orig = max((len(t) for t in texts), default=0)
    if max_chars <= 0:
        return list(texts), 0, max_orig
    out: list[str] = []
    truncated = 0
    for t in texts:
        if len(t) > max_chars:
            out.append(t[:max_chars])
            truncated += 1
        else:
            out.append(t)
    return out, truncated, max_orig


def _batches(texts: list[str], max_count: int, max_chars: int):
    """Splits `texts` in batches onder zowel het aantal- als het cumulatieve tekenbudget.

    Yields `(start_index, sublist)` zodat de aanroeper de resultaten op hun oorspronkelijke
    positie terugplaatst. Een enkele tekst die (al getrunceerd) tóch het char-budget overschrijdt
    krijgt een eigen batch — kleiner kan niet zonder data te knippen.
    """
    batch: list[str] = []
    batch_chars = 0
    start = 0
    for i, t in enumerate(texts):
        too_many = max_count > 0 and len(batch) >= max_count
        too_big = max_chars > 0 and batch and (batch_chars + len(t)) > max_chars
        if too_many or too_big:
            yield start, batch
            batch, batch_chars, start = [], 0, i
        batch.append(t)
        batch_chars += len(t)
    if batch:
        yield start, batch
