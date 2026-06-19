"""Sovereign smoke-run: model-in-the-loop bedrading (Ollama + Qwen3), CPU-only.

Dit is een **bedradingstest, geen prestatietest**. Een groene run bewijst dat het
sovereign-profiel met een model in de lus correct bedraad is — niet dat het snel/goed genoeg
is. Trek geen prestatieconclusies uit CPU-timings.

Draait alleen wanneer `ZEEF_SMOKE=1` én er een Ollama-server bereikbaar is; anders geskipt,
zodat de gewone (offline) testsuite groen blijft. Run expliciet met:

    ZEEF_SMOKE=1 uv run pytest tests/test_sovereign_smoke.py -s

Drie harde assertions (de test FAALT bij elke schending):
  1. De LLM-fallback is écht afgegaan (≥1 `llm-decision`-event in audit.jsonl).
  2. Transparantie is echt: elk LLM-event draagt een niet-lege model-id, `location == "local"`
     en een niet-lege exacte prompt.
  3. Sovereign bleef sovereign: geen enkele providercall verliet de machine (alleen loopback).
"""

import json
import os
import socket
import urllib.request
from pathlib import Path

import pytest

from zeef.audit import AuditLog
from zeef.config import CutoffMode, ProfileName, Settings
from zeef.pipeline.run import run_converge
from zeef.profiles import resolve_providers

CORPUS = Path(__file__).resolve().parent / "fixtures" / "corpus"
QUERY = "begroting subsidie cultuur 2026"
_LOOPBACK = {"127.0.0.1", "::1"}


def _ollama_up(host: str) -> bool:
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=3) as resp:
            return resp.status == 200
    except OSError:
        return False


def _smoke_env() -> Settings:
    # Bekende kleine modellen, tenzij de omgeving ze overschrijft.
    os.environ.setdefault("ZEEF_OLLAMA_HOST", "http://127.0.0.1:11434")
    os.environ.setdefault("ZEEF_OLLAMA_LLM_MODEL", "qwen3:0.6b")
    os.environ.setdefault("ZEEF_SOVEREIGN_EMBED", "ollama")
    os.environ.setdefault("ZEEF_OLLAMA_EMBED_MODEL", "qwen3-embedding:0.6b")
    return Settings(_env_file=None)


pytestmark = pytest.mark.skipif(
    os.environ.get("ZEEF_SMOKE") != "1", reason="sovereign smoke-run: zet ZEEF_SMOKE=1"
)


@pytest.fixture
def loopback_only(monkeypatch):
    """Sta alleen loopback-verbindingen toe; elke externe poging faalt hard (assertion 3)."""
    blocked: list = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def _host_ok(address) -> bool:
        if not isinstance(address, tuple):  # AF_UNIX e.d. → lokaal
            return True
        return str(address[0]) in _LOOPBACK or str(address[0]).startswith("127.")

    def guard_connect(self, address):
        if not _host_ok(address):
            blocked.append(address)
            raise OSError(f"egress geblokkeerd (sovereign): {address}")
        return real_connect(self, address)

    def guard_connect_ex(self, address):
        if not _host_ok(address):
            blocked.append(address)
            raise OSError(f"egress geblokkeerd (sovereign): {address}")
        return real_connect_ex(self, address)

    monkeypatch.setattr(socket.socket, "connect", guard_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guard_connect_ex)
    return blocked


def test_sovereign_model_in_the_loop(tmp_path, loopback_only):
    settings = _smoke_env()
    if not _ollama_up(settings.ollama_host):
        pytest.skip(f"geen Ollama op {settings.ollama_host}")

    providers = resolve_providers(ProfileName.sovereign, no_llm=False, settings=settings)
    audit = AuditLog(tmp_path / "audit.jsonl")
    result = run_converge(CORPUS, QUERY, providers, CutoffMode.target, 100, tmp_path, audit)

    events = [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text().splitlines()]
    llm_events = [e for e in events if e["action"] == "llm-decision"]

    # Bewijs voor de rapportage.
    print(f"\n[smoke] LLM-model        : {settings.ollama_llm_model}")
    print(f"[smoke] embed-model      : {settings.ollama_embed_model} (sovereign_embed=ollama)")
    print(f"[smoke] documenten       : {result.counts()}")
    print(f"[smoke] LLM-fallback op  : {len(llm_events)} document(en)")
    print(f"[smoke] geblokkeerde egress-pogingen: {len(loopback_only)}")
    for e in llm_events[:3]:
        print(f"[smoke]   event: model={e.get('model')} location={e.get('location')} "
              f"prompt[:50]={e.get('prompt','')[:50]!r}")

    # Assertion 1 — de LLM-fallback is écht afgegaan.
    assert llm_events, "geen enkele llm-decision in audit.jsonl: LLM-pad nooit uitgeoefend"

    # Assertion 2 — transparantie is echt voor élk LLM-event.
    for e in llm_events:
        assert e.get("model"), f"LLM-event zonder model-id: {e}"
        assert e.get("location") == "local", f"LLM-event location != local: {e}"
        assert e.get("prompt", "").strip(), f"LLM-event zonder exacte prompt: {e}"
        assert QUERY in e["prompt"], "exacte prompt mist de zoekvraag"

    # Assertion 3 — sovereign bleef sovereign (geen externe call).
    assert loopback_only == [], f"externe netwerkcall(s) onder sovereign: {loopback_only}"

    # Drie artefacten aanwezig (sanity).
    for name in ("inventory.xlsx", "relations.json", "audit.jsonl"):
        assert (tmp_path / name).exists(), name
