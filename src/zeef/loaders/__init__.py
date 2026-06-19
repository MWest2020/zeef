"""Loader-registry — selecteert per bestand de eerste passende `Loader` (ingest-spec).

De pijplijn hardcodeert geen formaatafhandeling: ze vraagt de registry om een loader. Nieuwe
formaten = een extra `Loader` in deze lijst, geen wijziging aan de stages.
"""

from __future__ import annotations

from pathlib import Path

from zeef.loaders.email_loader import EmailLoader
from zeef.loaders.pdf_loader import PdfLoader
from zeef.protocols import Loader

__all__ = ["EmailLoader", "PdfLoader", "default_loaders", "select_loader"]


def default_loaders() -> list[Loader]:
    """De standaard-loaderset, op volgorde van selectie."""
    return [EmailLoader(), PdfLoader()]


def select_loader(path: Path, loaders: list[Loader]) -> Loader | None:
    """Geef de eerste loader waarvan `can_load` waar is, of None."""
    for loader in loaders:
        if loader.can_load(path):
            return loader
    return None
