"""Voyage transport-hardening: per-input truncatie + batching, request-grenzen, auditbaarheid.

De drivers praten niet live met Voyage in deze test: we vervangen `_client._post` door een fake
die de payloads registreert. Bewezen wordt het contract dat de pijplijn aanneemt — één
vector/score per input, in oorspronkelijke volgorde — plus dat geen batch de geconfigureerde
grenzen overschrijdt, dat truncatie zichtbaar is, en dat rerank NIET splitst maar hard faalt als
het niet in één call past (design D-RERANK-SPLIT).
"""

from __future__ import annotations

import urllib.error

import pytest

from zeef.drivers import voyage as voyage_mod
from zeef.drivers.voyage import VoyageEmbed, VoyageReranker, _batches, _truncate


class _FakeResp:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return b'{"ok": true}'


def _http_error(code, retry_after=None):
    hdrs = {"Retry-After": retry_after} if retry_after is not None else {}
    return urllib.error.HTTPError("https://api.voyageai.com/v1/embeddings", code, "x", hdrs, None)


# --- helpers: fakes die de echte HTTP-call vervangen ---------------------------------------


def _fake_embed_post(recorder):
    def _post(path, payload):
        assert path == "/embeddings"
        recorder.append(payload["input"])
        # Voyage geeft per input een index + embedding; één-dim vector = de tekstlengte (uniek genoeg
        # om volgorde te kunnen verifiëren).
        return {"data": [{"index": i, "embedding": [float(len(t))]}
                         for i, t in enumerate(payload["input"])]}
    return _post


def _fake_rerank_post(recorder):
    def _post(path, payload):
        assert path == "/rerank"
        recorder.append(payload["documents"])
        return {"data": [{"index": i, "relevance_score": float(len(d))}
                         for i, d in enumerate(payload["documents"])]}
    return _post


# --- _truncate -----------------------------------------------------------------------------


def test_truncate_caps_and_counts():
    out, truncated, max_orig = _truncate(["abc", "abcdefgh", "x"], max_chars=4)
    assert out == ["abc", "abcd", "x"]
    assert truncated == 1
    assert max_orig == 8


def test_truncate_disabled_when_zero():
    out, truncated, max_orig = _truncate(["abcdefgh"], max_chars=0)
    assert out == ["abcdefgh"]
    assert truncated == 0
    assert max_orig == 8


# --- _batches ------------------------------------------------------------------------------


def test_batches_respect_count_limit():
    texts = [f"t{i}" for i in range(10)]
    batches = list(_batches(texts, max_count=3, max_chars=0))
    assert [len(b) for _, b in batches] == [3, 3, 3, 1]
    # Start-indices kloppen en dekken de hele lijst in volgorde.
    assert [s for s, _ in batches] == [0, 3, 6, 9]
    assert [t for _, b in batches for t in b] == texts


def test_batches_respect_char_budget():
    texts = ["aaaa", "bbbb", "cccc"]  # 4 chars elk
    batches = list(_batches(texts, max_count=0, max_chars=8))
    # Budget 8 → max 2 per batch.
    assert all(sum(len(t) for t in b) <= 8 for _, b in batches)
    assert [t for _, b in batches for t in b] == texts


def test_batches_oversized_single_input_gets_own_batch():
    texts = ["aa", "x" * 100, "bb"]
    batches = list(_batches(texts, max_count=0, max_chars=10))
    # De te grote tekst staat alleen in een eigen batch (kan niet kleiner).
    assert any(len(b) == 1 and len(b[0]) == 100 for _, b in batches)
    assert [t for _, b in batches for t in b] == texts


# --- VoyageEmbed ---------------------------------------------------------------------------


def test_embed_preserves_order_across_batches():
    sent: list[list[str]] = []
    embed = VoyageEmbed(api_key="x", embed_chars=0, batch_size=2, batch_chars=0)
    embed._client._post = _fake_embed_post(sent)
    texts = ["a", "bb", "ccc", "dddd", "eeeee"]
    vecs = embed.embed(texts)
    # Eén vector per input, in oorspronkelijke volgorde (vec = [len(text)]).
    assert vecs == [[1.0], [2.0], [3.0], [4.0], [5.0]]
    # Meerdere batches, elk ≤ batch_size.
    assert len(sent) == 3
    assert all(len(b) <= 2 for b in sent)


def test_embed_truncates_and_reports_stats():
    sent: list[list[str]] = []
    embed = VoyageEmbed(api_key="x", embed_chars=3, batch_size=10, batch_chars=0)
    embed._client._post = _fake_embed_post(sent)
    embed.embed(["abcdef", "gh"])
    # De te lange input is op 3 tekens gekapt vóór verzenden.
    assert sent == [["abc", "gh"]]
    stats = embed.transport_stats()
    assert stats["truncated_inputs"] == 1
    assert stats["max_original_len"] == 6
    assert stats["embed_chars"] == 3
    assert stats["split"] is True


# --- VoyageReranker ------------------------------------------------------------------------


def test_rerank_single_call_preserves_order():
    sent: list[list[str]] = []
    rr = VoyageReranker(api_key="x", rerank_chars=0, max_total_tokens=10_000_000)
    rr._client._post = _fake_rerank_post(sent)
    scores = rr.rerank("q", ["a", "bb", "ccc"])
    assert scores == [1.0, 2.0, 3.0]
    # Eén enkele call: rerank wordt NIET gesplitst (D-RERANK-SPLIT).
    assert len(sent) == 1
    assert rr.transport_stats()["split"] is False


def test_rerank_truncates_documents():
    sent: list[list[str]] = []
    rr = VoyageReranker(api_key="x", rerank_chars=2, max_total_tokens=10_000_000)
    rr._client._post = _fake_rerank_post(sent)
    rr.rerank("q", ["abcdef", "gh"])
    assert sent == [["ab", "gh"]]
    assert rr.transport_stats()["truncated_docs"] == 1


def test_rerank_fails_loudly_over_token_budget():
    rr = VoyageReranker(api_key="x", rerank_chars=0, max_total_tokens=10)
    rr._client._post = _fake_rerank_post([])
    # Geen split → over budget moet hard falen, niet stil knippen of splitsen.
    with pytest.raises(RuntimeError, match="splitsen niet"):
        rr.rerank("query", ["x" * 1000])


def test_rerank_fails_loudly_over_doc_limit():
    rr = VoyageReranker(api_key="x", rerank_chars=0, max_total_tokens=10_000_000, max_docs=2)
    rr._client._post = _fake_rerank_post([])
    with pytest.raises(RuntimeError, match="docs >"):
        rr.rerank("q", ["a", "b", "c"])


# --- retry/back-off op transiente fouten (429/5xx) -----------------------------------------


def test_post_retries_on_429_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def fake_urlopen(req):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _http_error(429, retry_after="0")
        return _FakeResp()

    monkeypatch.setattr(voyage_mod.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(voyage_mod.time, "sleep", lambda s: None)
    client = voyage_mod._VoyageClient("k")
    out = client._post("/embeddings", {"x": 1})
    assert out == {"ok": True}
    assert calls["n"] == 2  # eenmaal gefaald (429), eenmaal gelukt
    assert client._retries == 1


def test_post_does_not_retry_on_400(monkeypatch):
    def fake_urlopen(req):
        raise _http_error(400)

    monkeypatch.setattr(voyage_mod.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(voyage_mod.time, "sleep", lambda s: None)
    client = voyage_mod._VoyageClient("k")
    with pytest.raises(urllib.error.HTTPError):
        client._post("/embeddings", {"x": 1})
    assert client._retries == 0  # 4xx-anders = geen retry, fail loud
