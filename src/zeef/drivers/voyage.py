"""Voyage-drivers: hosted embedding + rerank, request-grens-bewust (truncatie + batching).

Voyage bound elke request (max 1.000 inputs; per-request tokenbudget; query+doc ≤ 16K tok bij
rerank). Deze drivers houden zich daar deterministisch aan: elke input wordt client-side op een
char-budget getrunceerd (reproduceerbaar/auditbaar, niet stil server-side) en de embed-lijst in
batches onder een aantal- én tekenbudget gesplitst. Rerank wordt NIET gesplitst (de Voyage-docs
bevestigen niet dat de score batch-onafhankelijk is, design D-RERANK-SPLIT) maar getrunceerd zodat
de set in één call past; lukt dat niet, dan faalt de driver hard. Sleutel uit `VOYAGE_API_KEY`.
"""

from __future__ import annotations

import json
import os
import urllib.request

from zeef.drivers.cloud import _require

VOYAGE_EMBED_MODEL = "voyage-3"
VOYAGE_RERANK_MODEL = "rerank-2"

# Conservatieve token-schatting (Voyage ~3-4 tekens/token NL): delen door 3 overschat tokens, dus
# de grens grijpt vroeger in (veilig) i.p.v. een echte 400 te riskeren.
_CHARS_PER_TOKEN_EST = 3


class _VoyageClient:
    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key or os.environ.get("VOYAGE_API_KEY")

    def _post(self, path: str, payload: dict) -> dict:
        key = _require(self._api_key, "VOYAGE_API_KEY")
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.voyageai.com/v1{path}",
            data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req) as resp:  # noqa: S310 — vaste, getrouste host
            return json.loads(resp.read().decode("utf-8"))


def _truncate(texts: list[str], max_chars: int) -> tuple[list[str], int, int]:
    """Kap elke tekst op `max_chars` (≤0 = uit). Geeft (gekapte_lijst, aantal_gekapt, max_orig_len).

    Truncatie is deterministisch (eerste `max_chars` tekens) en client-side, zodat de toegepaste
    grens reproduceerbaar en auditbaar is i.p.v. server-side stil afgekapt.
    """
    max_orig = max((len(t) for t in texts), default=0)
    if max_chars <= 0:
        return list(texts), 0, max_orig
    out: list[str] = []
    truncated = 0
    for t in texts:
        if len(t) > max_chars:
            out.append(t[:max_chars])
            truncated += 1
        else:
            out.append(t)
    return out, truncated, max_orig


def _batches(texts: list[str], max_count: int, max_chars: int):
    """Splits `texts` in batches onder zowel het aantal- als het cumulatieve tekenbudget.

    Yields `(start_index, sublist)` zodat de aanroeper de resultaten op hun oorspronkelijke
    positie terugplaatst. Een enkele tekst die (al getrunceerd) tóch het char-budget overschrijdt
    krijgt een eigen batch — kleiner kan niet zonder data te knippen.
    """
    batch: list[str] = []
    batch_chars = 0
    start = 0
    for i, t in enumerate(texts):
        too_many = max_count > 0 and len(batch) >= max_count
        too_big = max_chars > 0 and batch and (batch_chars + len(t)) > max_chars
        if too_many or too_big:
            yield start, batch
            batch, batch_chars, start = [], 0, i
        batch.append(t)
        batch_chars += len(t)
    if batch:
        yield start, batch


class VoyageEmbed:
    """Hosted embeddings via Voyage AI. Sleutel uit `VOYAGE_API_KEY`.

    Bound elke request aan de Voyage-limieten: elke input wordt op `embed_chars` getrunceerd en de
    lijst in batches onder `batch_size`/`batch_chars` gesplitst, sequentieel gepost en in
    oorspronkelijke volgorde teruggegeven. Batchen is exact — elke input embed onafhankelijk, dus
    splitsen verandert geen enkele vector. Caps en truncatie-telling via `transport_stats()`.
    """

    location = "cloud"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = VOYAGE_EMBED_MODEL,
        *,
        embed_chars: int = 16000,
        batch_size: int = 64,
        batch_chars: int = 300000,
    ) -> None:
        self._client = _VoyageClient(api_key)
        self.model = model
        self.name = f"voyage:{model}"
        self.embed_chars = embed_chars
        self.batch_size = batch_size
        self.batch_chars = batch_chars
        self._truncated_inputs = 0
        self._max_original_len = 0
        self._requests = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        prepared, truncated, max_orig = _truncate(texts, self.embed_chars)
        self._truncated_inputs += truncated
        self._max_original_len = max(self._max_original_len, max_orig)
        out: list[list[float] | None] = [None] * len(prepared)
        for start, batch in _batches(prepared, self.batch_size, self.batch_chars):
            res = self._client._post("/embeddings", {"model": self.model, "input": batch})
            self._requests += 1
            for row in res["data"]:
                out[start + int(row["index"])] = [float(x) for x in row["embedding"]]
        return [v for v in out if v is not None]

    def transport_stats(self) -> dict:
        return {
            "endpoint": "embeddings", "model": self.model, "split": True,
            "embed_chars": self.embed_chars, "batch_size": self.batch_size,
            "batch_chars": self.batch_chars, "truncated_inputs": self._truncated_inputs,
            "max_original_len": self._max_original_len, "requests": self._requests,
        }


class VoyageReranker:
    """Hosted cross-encoder rerank via Voyage AI. Sleutel uit `VOYAGE_API_KEY`.

    BEWUSTE BEPERKING (design D-RERANK-SPLIT): de Voyage-docs bevestigen NIET dat `relevance_score`
    batch-onafhankelijk is. We splitsen daarom NIET (dat zou de selector laten gokken) maar
    trunceren elke doc op `rerank_chars` zodat de set in één call past. Past het dán nog niet in het
    tokenbudget (rerank-2: query_tok × n + Σ doc_tok ≤ 600K) of boven 1.000 docs, dan falen we hard.
    """

    location = "cloud"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = VOYAGE_RERANK_MODEL,
        *,
        rerank_chars: int = 4000,
        max_total_tokens: int = 550000,
        max_docs: int = 1000,
    ) -> None:
        self._client = _VoyageClient(api_key)
        self.model = model
        self.name = f"voyage:{model}"
        self.rerank_chars = rerank_chars
        self.max_total_tokens = max_total_tokens
        self.max_docs = max_docs
        self._truncated_docs = 0
        self._max_original_len = 0
        self._last_doc_count = 0
        self._last_est_tokens = 0

    def rerank(self, query: str, docs: list[str]) -> list[float]:
        prepared, truncated, max_orig = _truncate(docs, self.rerank_chars)
        self._truncated_docs += truncated
        self._max_original_len = max(self._max_original_len, max_orig)
        self._last_doc_count = len(prepared)
        q_tok = max(1, len(query) // _CHARS_PER_TOKEN_EST)
        doc_tok = sum(max(1, len(t) // _CHARS_PER_TOKEN_EST) for t in prepared)
        est_total = q_tok * len(prepared) + doc_tok
        self._last_est_tokens = est_total
        if len(prepared) > self.max_docs:
            raise RuntimeError(
                f"Voyage rerank: {len(prepared)} docs > limiet {self.max_docs}. We splitsen niet "
                "(score-onafhankelijkheid onbevestigd, design D-RERANK-SPLIT). Verklein de "
                "kandidatenset of bevestig batch-onafhankelijkheid eerst."
            )
        if est_total > self.max_total_tokens:
            raise RuntimeError(
                f"Voyage rerank: geschat {est_total} tokens > budget {self.max_total_tokens} bij "
                f"rerank_chars={self.rerank_chars}. We splitsen niet (D-RERANK-SPLIT). Verlaag "
                "rerank_chars of de kandidatenset."
            )
        res = self._client._post(
            "/rerank", {"model": self.model, "query": query, "documents": prepared}
        )
        ordered = sorted(res["data"], key=lambda r: r["index"])
        return [float(r["relevance_score"]) for r in ordered]

    def transport_stats(self) -> dict:
        return {
            "endpoint": "rerank", "model": self.model, "split": False,
            "rerank_chars": self.rerank_chars, "max_total_tokens": self.max_total_tokens,
            "truncated_docs": self._truncated_docs, "max_original_len": self._max_original_len,
            "last_doc_count": self._last_doc_count, "last_est_tokens": self._last_est_tokens,
        }
