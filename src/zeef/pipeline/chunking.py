"""Deterministische chunking (retrieve-spec): zelfde document + grootte → zelfde chunks.

Eenvoudige, voorspelbare vensters over de genormaliseerde tekst. Bewust deterministisch en
zonder model: reproduceerbaarheid boven slimheid. Korte documenten leveren één chunk.
"""

from __future__ import annotations

from zeef.models import Chunk, Document

DEFAULT_CHUNK_SIZE = 1000


def chunk_document(doc: Document, chunk_size: int = DEFAULT_CHUNK_SIZE) -> list[Chunk]:
    """Splits `doc.text` in geordende chunks van maximaal `chunk_size` tekens."""
    text = doc.text
    if not text:
        return []
    pieces = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)] or [text]
    chunks = [
        Chunk(id=f"{doc.id}:{ordinal}", ordinal=ordinal, text=piece)
        for ordinal, piece in enumerate(pieces)
    ]
    doc.chunks = chunks
    return chunks
