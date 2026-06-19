"""Content-geadresseerde document-id (D2) — bewust een losstaand, afhankelijkheidsvrij module.

Dit bestand importeert *alleen* de standaardbibliotheek. Een los repo (bijv. `zeef-eval`)
kan `from zeef.ids import content_id` doen zonder de hele pijplijn (pydantic, drivers, …)
binnen te halen. Zo kan het cross-repo `doc_id`-contract niet uit elkaar lopen: er is precies
één afleiding, hier.

De afleiding is bevroren — wijzig haar niet zonder een expliciete migratie, want bestaande
ids (en cross-repo verwijzingen) zouden er door breken.
"""

from __future__ import annotations

import hashlib

# Aantal hex-tekens van de content-hash dat als id wordt gebruikt (D2).
ID_LENGTH = 16


def content_id(normalized_text: str, source_path: str) -> str:
    """Deterministische, content-geadresseerde id (D2).

    `sha256(normalized_text + b"\\x00" + source_path)`, afgekapt op `ID_LENGTH` hex-tekens.
    Een herhaalde run levert dezelfde id (reproduceerbaarheid); exacte dubbelingen vallen op
    omdat de tekst gelijk is, terwijl het herkomstpad twee echt verschillende bestanden met
    dezelfde tekst onderscheidbaar houdt. De NUL-byte scheidt tekst en pad ondubbelzinnig.
    """
    digest = hashlib.sha256()
    digest.update(normalized_text.encode("utf-8"))
    digest.update(b"\x00")
    digest.update(source_path.encode("utf-8"))
    return digest.hexdigest()[:ID_LENGTH]
