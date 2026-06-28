"""Relate / driver-level voortgang (observe-relate-progress): de embed-driver roept een optionele
progress-callback aan per item; relate geeft 'm door tijdens de near-dup-embedding. No-op zonder
callback, resultaten ongemoeid.
"""

import pytest

from zeef.audit import AuditLog
from zeef.config import ProfileName, Settings
from zeef.drivers.local import HashingEmbed
from zeef.models import Document
from zeef.observe import StageObserver
from zeef.pipeline.relate import relate
from zeef.profiles import resolve_providers


def _doc(doc_id: str, text: str) -> Document:
    return Document(id=doc_id, source_path=f"/{doc_id}", doc_type="other", text=text)


# --- driver-level progress --------------------------------------------------------------


def test_embed_progress_fires_per_text():
    calls: list[tuple[int, int]] = []
    HashingEmbed().embed(["a", "b", "c"], progress=lambda d, t: calls.append((d, t)))
    assert calls == [(1, 3), (2, 3), (3, 3)]


def test_embed_progress_none_is_noop_and_identical():
    texts = ["begroting", "subsidie", "cultuur"]
    a = HashingEmbed().embed(texts)
    b = HashingEmbed().embed(texts, progress=None)
    assert a == b  # zelfde vectoren, progress raakt de uitkomst niet


# --- relate geeft progress door tijdens de near-dup-embedding ---------------------------


def test_relate_reports_progress(tmp_path):
    pytest.importorskip("datasketch")
    audit = AuditLog(tmp_path / "a.jsonl")
    docs = [_doc(f"d{i}", f"begroting subsidie cultuur {i}") for i in range(6)]
    calls: list[tuple[int, int]] = []
    relate(docs, HashingEmbed(), audit, progress=lambda d, t: calls.append((d, t)))
    assert calls, "verwachtte progress-calls tijdens near-dup-embedding"
    assert calls[-1][0] == calls[-1][1]  # laatste call is (N, N)
    assert all(t == calls[0][1] for _, t in calls)  # totaal stabiel


def test_relate_progress_none_is_noop(tmp_path):
    pytest.importorskip("datasketch")
    audit = AuditLog(tmp_path / "a.jsonl")
    docs = [_doc(f"d{i}", f"tekst {i}") for i in range(4)]
    relate(docs, HashingEmbed(), audit, progress=None)  # mag niet falen


# --- relate-verb in de observer ---------------------------------------------------------


def test_progress_for_relate_labels_correctly(tmp_path, capsys):
    audit = AuditLog(tmp_path / "a.jsonl")
    audit.event("cli", "start")
    providers = resolve_providers(ProfileName.sovereign, no_llm=True, settings=Settings(_env_file=None))
    StageObserver(audit.path, providers).progress_for("relate")(10, 10)
    assert "relate: embedded 10/10" in capsys.readouterr().out
