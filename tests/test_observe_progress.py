"""Observe live-voortgang (observe-embed-progress): per-item teller in ingest/retrieve, no-op
als observe uit staat, resultaten ongemoeid, en het criteria-paneel toont de echte zoekvraag.
"""

import pytest

from zeef.audit import AuditLog
from zeef.config import CutoffMode, ProfileName, Settings
from zeef.drivers.local import HashingEmbed
from zeef.models import Document
from zeef.observe import StageObserver
from zeef.observe_blocks import build
from zeef.pipeline.ingest import ingest
from zeef.pipeline.retrieve import retrieve
from zeef.pipeline.run import run_converge
from zeef.profiles import resolve_providers

QUERY = "begroting subsidie cultuur 2026"


def _doc(doc_id: str, text: str) -> Document:
    return Document(id=doc_id, source_path=f"/{doc_id}", doc_type="other", text=text)


# --- per-item callback in retrieve ------------------------------------------------------


def test_retrieve_progress_fires_per_candidate(tmp_path):
    audit = AuditLog(tmp_path / "a.jsonl")
    docs = [_doc(f"d{i}", f"begroting {i}") for i in range(5)]
    calls: list[tuple[int, int]] = []
    retrieve(docs, HashingEmbed(), audit, QUERY, progress=lambda d, t: calls.append((d, t)))
    assert len(calls) == 5
    assert calls[0] == (1, 5)
    assert calls[-1] == (5, 5)  # laatste call is altijd (N, N)


def test_retrieve_progress_does_not_change_scores(tmp_path):
    docs_a = [_doc(f"d{i}", f"begroting subsidie {i}") for i in range(4)]
    docs_b = [_doc(f"d{i}", f"begroting subsidie {i}") for i in range(4)]
    retrieve(docs_a, HashingEmbed(), AuditLog(tmp_path / "a.jsonl"), QUERY)
    retrieve(docs_b, HashingEmbed(), AuditLog(tmp_path / "b.jsonl"), QUERY,
             progress=lambda d, t: None)
    assert [d.scores["final"] for d in docs_a] == [d.scores["final"] for d in docs_b]


def test_retrieve_progress_none_is_noop(tmp_path):
    audit = AuditLog(tmp_path / "a.jsonl")
    docs = [_doc("a", "begroting"), _doc("b", "fietsen")]
    cands = retrieve(docs, HashingEmbed(), audit, QUERY, progress=None)
    assert all("final" in d.scores for d in cands)


# --- per-item callback in ingest --------------------------------------------------------


def test_ingest_progress_counts_files(corpus, tmp_path):
    audit = AuditLog(tmp_path / "a.jsonl")
    calls: list[tuple[int, int]] = []
    ingest(corpus, audit, progress=lambda d, t: calls.append((d, t)))
    assert calls, "verwachtte minstens één voortgangs-call"
    total = calls[0][1]
    assert all(t == total for _, t in calls)  # totaal stabiel
    assert [d for d, _ in calls] == list(range(1, total + 1))  # 1..N, geen sprongen


# --- StageObserver.progress_for: begrensde, throttled output ----------------------------


def test_progress_for_throttles_and_is_dim(tmp_path, capsys):
    audit = AuditLog(tmp_path / "a.jsonl")
    audit.event("cli", "start")  # zorg dat het bestand bestaat
    providers = resolve_providers(ProfileName.sovereign, no_llm=True, settings=Settings(_env_file=None))
    cb = StageObserver(audit.path, providers).progress_for("retrieve")
    for i in range(1, 101):
        cb(i, 100)
    out = capsys.readouterr().out
    n_lines = out.count("retrieve: embedded")
    assert 0 < n_lines <= 21  # ~20 updates, niet 100 (geen per-document spam)
    assert "100/100" in out  # laatste item altijd getoond


def test_progress_for_zero_total_prints_nothing(tmp_path, capsys):
    audit = AuditLog(tmp_path / "a.jsonl")
    audit.event("cli", "start")
    providers = resolve_providers(ProfileName.sovereign, no_llm=True, settings=Settings(_env_file=None))
    StageObserver(audit.path, providers).progress_for("ingest")(0, 0)
    assert capsys.readouterr().out == ""


# --- criteria-paneel toont de echte zoekvraag (--no-llm fallback) -----------------------


def test_criteria_panel_shows_query():
    q = "Alle documenten over de invoering van de Omgevingswet en het DSO en de vertraging"
    events = [{"stage": "criteria", "action": "fallback", "inputs": {"query": q}}]
    block = build("criteria", events, lambda role: ("?", "local"))
    assert "Omgevingswet" in block["input"]  # de echte vraag, niet alleen "zoekvraag"
    assert block["input"] != "zoekvraag"


def test_criteria_panel_without_query_falls_back():
    events = [{"stage": "criteria", "action": "fallback", "inputs": {}}]
    block = build("criteria", events, lambda role: ("?", "local"))
    assert block["input"] == "zoekvraag"


# --- regressie: observe aan/uit geeft identieke selectie --------------------------------


@pytest.fixture
def no_network(monkeypatch):
    import socket

    def guard(*args, **kwargs):
        raise OSError("netwerk uit in test")

    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket.socket, "connect_ex", guard)
    monkeypatch.setattr(socket, "create_connection", guard)


def _run(corpus, out_dir, observe):
    providers = resolve_providers(ProfileName.sovereign, no_llm=True, settings=Settings(_env_file=None))
    audit = AuditLog(out_dir / "audit.jsonl")
    return run_converge(corpus, QUERY, providers, CutoffMode.target, 100, out_dir, audit,
                        observe=observe)


def _sel(r):
    return sorted(d.id for d in r.selected)


def _dec(r):
    return sorted((d.id, d.decision, d.scores.get("final")) for d in r.documents)


def test_observe_does_not_change_selection(corpus, tmp_path, no_network):
    off = _run(corpus, tmp_path / "off", observe=False)
    on = _run(corpus, tmp_path / "on", observe=True)
    assert _sel(off) == _sel(on)
    assert _dec(off) == _dec(on)
