"""Canoniek datamodel — de spil van de hele pijplijn.

Elk inkomend bestand, ongeacht formaat, wordt genormaliseerd naar één `Document`.
Alle stages lezen en schrijven dit model; scores en beslissingen stapelen zich erop.
Zie design.md (D1, D2, D3) voor de rationale.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# De id-afleiding leeft in een losstaand, afhankelijkheidsvrij module (zie zeef/ids.py),
# zodat een ander repo het `doc_id`-contract kan importeren zonder de pijplijn. Hier
# her-exporteren we het voor bestaande imports (`from zeef.models import content_id`).
from zeef.ids import ID_LENGTH, content_id

__all__ = [
    "Chunk", "Relation", "Document", "Criterion", "Criteria",
    "content_id", "ID_LENGTH",
]

DocType = Literal["email", "pdf_digital", "pdf_scanned", "office", "other"]
RelationKind = Literal["thread-parent", "attachment-of", "duplicate-of", "overlaps-with"]
Decision = Literal["selected", "out_of_scope", "undecided"]


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
    rationale: str = ""  # per-document relevantie-motivatie (LLM); los van decision_reason
    best_passage: str = ""  # de chunk met de hoogste cosine t.o.v. de zoekvraag — de
    # deterministische "why" (converge-ranking D23); leeg vóór de retrieve-stage
    topic: str = ""  # onderwerp-label uit topic-clustering (deelonderwerp-menu); leeg vóór die stage
    subtopic: str = ""  # deelonderwerp-label, genest binnen `topic`

    def add_relation(self, kind: RelationKind, target_id: str, evidence: str) -> None:
        """Voeg een relatie toe (idempotent op (kind, target_id))."""
        for existing in self.relations:
            if existing.kind == kind and existing.target_id == target_id:
                return
        self.relations.append(Relation(kind=kind, target_id=target_id, evidence=evidence))


class Criterion(BaseModel):
    """Eén expliciet, benoembaar relevantiecriterium (label + omschrijving)."""

    label: str
    description: str


class Criteria(BaseModel):
    """De gearticuleerde relevantiedefinitie van een run — de toetssteen voor scoring.

    `source` is `"llm"` wanneer een LLM de criteria afleidde, of `"fallback"` wanneer er
    onder `--no-llm` één criterium gelijk aan de ruwe zoekvraag is gemaakt.
    """

    query: str
    items: list[Criterion] = Field(default_factory=list)
    source: Literal["llm", "fallback"] = "fallback"

    def as_prompt_block(self) -> str:
        """Criteria als genummerde regels voor in een scoring-prompt."""
        return "\n".join(f"{i}. {c.label}: {c.description}" for i, c in enumerate(self.items, 1))
