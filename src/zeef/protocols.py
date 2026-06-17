"""Alle interfaces (Protocols) op één plek — concrete drivers leven apart.

De pijplijn-stages krijgen deze providers geïnjecteerd en importeren nooit een concrete
driver. Dat is precies wat `cloud` ↔ `sovereign` tot een vlag maakt i.p.v. een codewijziging
(zie design.md, D3/D4).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from zeef.models import Document


@runtime_checkable
class Loader(Protocol):
    """Laadt één bronbestand naar één of meer `Document`s (een .eml = body + bijlagen)."""

    def can_load(self, path: Path) -> bool: ...

    def load(self, path: Path) -> list[Document]: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Zet teksten om naar embedding-vectoren."""

    def embed(self, texts: list[str]) -> list[list[float]]: ...


@runtime_checkable
class RerankerProvider(Protocol):
    """Geeft per document een relevantiescore t.o.v. de zoekvraag (cross-encoder of LLM)."""

    def rerank(self, query: str, docs: list[str]) -> list[float]: ...


@runtime_checkable
class LLMProvider(Protocol):
    """Generatieve stap (scope-twijfelgevallen, later cluster-labels/samenvatting)."""

    name: str
    location: str  # "local" | "cloud" — wordt in de audit-log vastgelegd

    def complete(self, prompt: str, *, system: str | None = None) -> str: ...
