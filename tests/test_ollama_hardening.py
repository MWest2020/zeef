"""Hardening van `OllamaEmbed` (driver): één retry op een transiënte fout, dan een uniforme
nulvector-fallback van de onthouden modeldimensie. Zo crasht een grote run niet op een enkele
HTTP 500 of een lege invoer, en blijven de vectorlengtes uniform (cosine eist dat). Geen netwerk:
de HTTP-client wordt gestubd; `time.sleep` is uitgezet zodat de retry niet echt wacht."""

import http.client
import urllib.error

import pytest

from zeef.drivers import ollama
from zeef.drivers.ollama import OllamaEmbed


def _reset(*_):
    # Wat Ollama onder zware sustained belasting doet: verbinding dicht zonder respons.
    raise http.client.RemoteDisconnected("Remote end closed connection without response")

DIM = 8


def _embed():
    return OllamaEmbed("http://localhost:11434", "test-model")


def _http500(*_):
    raise urllib.error.HTTPError("http://x", 500, "boom", {}, None)


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(ollama.time, "sleep", lambda *_: None)


def test_failing_text_falls_back_to_uniform_zero_vector():
    e = _embed()
    calls = {"n": 0}

    def post(_path, payload):
        calls["n"] += 1
        if "bad" in payload["prompt"]:
            raise urllib.error.HTTPError("http://x", 500, "boom", {}, None)
        return {"embedding": [0.1] * DIM}

    e._client._post = post
    out = e.embed(["good text", "bad text"])
    assert [len(v) for v in out] == [DIM, DIM]          # uniforme lengtes
    assert any(x != 0 for x in out[0])                  # succes = echte vector
    assert all(x == 0 for x in out[1])                  # mislukt = nulvector van modeldim
    assert calls["n"] == 3                              # 1× good + 2× bad (één retry)


def test_empty_input_yields_zero_vector_without_a_call():
    e = _embed()
    calls = {"n": 0}

    def post(_path, _payload):
        calls["n"] += 1
        return {"embedding": [0.1] * DIM}

    e._client._post = post
    out = e.embed(["good", "   \n\t "])
    assert [len(v) for v in out] == [DIM, DIM]
    assert all(x == 0 for x in out[1])
    assert calls["n"] == 1                              # lege/whitespace-invoer doet geen call


def test_dimension_remembered_across_calls():
    e = _embed()
    e._client._post = lambda _p, _pl: {"embedding": [0.2] * DIM}
    e.embed(["seed"])                                   # leert de modeldimensie
    e._client._post = _http500
    out = e.embed(["all fail now"])
    assert [len(v) for v in out] == [DIM]               # uniforme nulvector van onthouden dim
    assert all(x == 0 for x in out[0])


def test_cold_total_failure_is_uniform_empty():
    e = _embed()
    e._client._post = lambda *_: (_ for _ in ()).throw(urllib.error.URLError("down"))
    out = e.embed(["a", "b"])
    assert out == [[], []]                              # dim nooit geleerd → uniforme lege vectoren


def test_remote_disconnected_is_caught_not_crash():
    # Regressie: RemoteDisconnected is OSError, GEEN URLError — moet tóch gevangen worden
    # (anders crasht relate op een groot/UNGECAPT corpus, zoals waargenomen).
    e = _embed()
    e._client._post = _reset
    out = e.embed(["a", "b"])                            # géén exception → afgevangen
    assert out == [[], []]


def test_remote_disconnected_after_success_yields_zero_vector():
    e = _embed()
    e._client._post = lambda *_: {"embedding": [0.3] * DIM}
    e.embed(["seed"])                                   # leert dimensie
    e._client._post = _reset
    out = e.embed(["dropped"])
    assert [len(v) for v in out] == [DIM] and all(x == 0 for x in out[0])
