"""Canoniek datamodel — de spil van de hele pijplijn.

Elk inkomend bestand, ongeacht formaat, wordt genormaliseerd naar één `Document`.
Alle stages lezen en schrijven dit model; scores en beslissingen stapelen zich erop.
Zie design.md (D1, D2, D3) voor de rationale.
"""

from __future__ import annotations

import hashlib
from typing import Any, Literal

from pydantic import BaseModel, Field

DocType = Literal["email", "pdf_digital", "pdf_scanned", "office", "other"]
RelationKind = Literal["thread-parent", "attachment-of", "duplicate-of", "overlaps-with"]
Decision = Literal["selected", "out_of_scope", "undecided"]

# Aantal hex-tekens van de content-hash dat als id wordt gebruikt (D2).
ID_LENGTH = 16


class Chunk(BaseModel):
    """Een deel van een lang document, alleen voor embedding/rerank."""

    id: str
    ordinal: int
    text: str
    embedding: list[float] | None = None


class Relation(BaseModel):
    """Een getypeerde relatie naar een ander document, mét bewijs.

    `evidence` legt vast wáárom de relatie is gelegd (headerwaarde, hash, cosinus),
    zodat de relatie achteraf navolgbaar is.
    """

    kind: RelationKind
    target_id: str
    evidence: str


class Document(BaseModel):
    """Het genormaliseerde document — de eenheid waarop de pijplijn werkt."""

    id: str
    source_path: str
    doc_type: DocType
    metadata: dict[str, Any] = Field(default_factory=dict)
    text: str = ""
    chunks: list[Chunk] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)
    decision: Decision = "undecided"
    decision_reason: str = ""

    def add_relation(self, kind: RelationKind, target_id: str, evidence: str) -> None:
        """Voeg een relatie toe (idempotent op (kind, target_id))."""
        for existing in self.relations:
            if existing.kind == kind and existing.target_id == target_id:
                return
        self.relations.append(Relation(kind=kind, target_id=target_id, evidence=evidence))


def content_id(normalized_text: str, source_path: str) -> str:
    """Deterministische, content-geadresseerde id (D2).

    Hash van genormaliseerde tekst + herkomstpad. Een herhaalde run levert dezelfde id
    (reproduceerbaarheid); exacte dubbelingen vallen op omdat de tekst gelijk is, terwijl
    het herkomstpad twee echt verschillende bestanden met dezelfde tekst onderscheidbaar houdt.
    """
    digest = hashlib.sha256()
    digest.update(normalized_text.encode("utf-8"))
    digest.update(b"\x00")
    digest.update(source_path.encode("utf-8"))
    return digest.hexdigest()[:ID_LENGTH]
