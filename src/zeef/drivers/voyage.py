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
import random
import sys
import time
import urllib.error
import urllib.request

from zeef.drivers._voyage_util import _CHARS_PER_TOKEN_EST, _batches, _truncate
from zeef.drivers.cloud import _require

# Re-export zodat bestaande importeurs/tests `_truncate`/`_batches` uit dit pad blijven vinden.
__all__ = ["VoyageEmbed", "VoyageReranker", "_truncate", "_batches"]

VOYAGE_EMBED_MODEL = "voyage-3"
VOYAGE_RERANK_MODEL = "rerank-2"

# Bounded retry op transiente Voyage-fouten (429 rate-limit, 5xx). De pijplijn mag niet stil
# omvallen op een rate-limit-hapering; we backen exponentieel af (en honoreren `Retry-After`),
# capped, met logging per poging. Geen retry op 4xx-anders (echte requestfouten — fail loud).
_MAX_RETRIES = 6
_BASE_DELAY_S = 2.0
_MAX_DELAY_S = 60.0


class _VoyageClient:
    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key or os.environ.get("VOYAGE_API_KEY")
        self._retries = 0

    def _post(self, path: str, payload: dict) -> dict:
        key = _require(self._api_key, "VOYAGE_API_KEY")
        data = json.dumps(payload).encode("utf-8")
        for attempt in range(_MAX_RETRIES + 1):
            req = urllib.request.Request(
                f"https://api.voyageai.com/v1{path}",
                data=data,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            )
            try:
                with urllib.request.urlopen(req) as resp:  # noqa: S310 — vaste, getrouste host
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if not retryable or attempt == _MAX_RETRIES:
                    raise
                delay = self._retry_delay(exc, attempt)
                self._retries += 1
                sys.stderr.write(
                    f"voyage: HTTP {exc.code} op {path}; retry {attempt + 1}/{_MAX_RETRIES} "
                    f"na {delay:.1f}s\n"
                )
                time.sleep(delay)
        raise RuntimeError("voyage: retry-lus eindigde zonder resultaat")  # pragma: no cover

    @staticmethod
    def _retry_delay(exc: urllib.error.HTTPError, attempt: int) -> float:
        retry_after = exc.headers.get("Retry-After") if exc.headers else None
        if retry_after and retry_after.strip().isdigit():
            return min(float(retry_after), _MAX_DELAY_S)
        return min(_BASE_DELAY_S * (2 ** attempt), _MAX_DELAY_S) + random.uniform(0, 0.5)


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
            "retries": self._client._retries,
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
            "retries": self._client._retries,
        }
