"""Gedeelde fixtures voor de testsuite."""

from pathlib import Path

import pytest

from zeef.audit import AuditLog

CORPUS = Path(__file__).resolve().parent / "fixtures" / "corpus"


@pytest.fixture
def corpus() -> Path:
    """Pad naar de gemengde .eml/PDF-fixtureset."""
    return CORPUS


@pytest.fixture
def audit(tmp_path) -> AuditLog:
    """Verse audit-log in een tijdelijke map."""
    return AuditLog(tmp_path / "audit.jsonl")
