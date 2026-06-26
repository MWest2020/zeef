## Why

The cloud drivers in `src/zeef/drivers/cloud.py` are not production-hardened. The CHANGELOG
records them as shipped but **"niet live getest"** (CHANGELOG line ~512: *"drivers/cloud.py
(Claude + Voyage, key-gated, niet live getest)"*). On a realistic corpus they crash, because
three call sites hand the full candidate set to a single Voyage request with no batching and no
per-input truncation:

- **`relate`** — `pipeline/dedup.py:56` embeds **all** non-empty document texts in one
  `embed.embed([...])` call. On a real Woo corpus (observed: 414 PDFs, 1.7 GB, median 1.6 MB,
  largest 73 MB) this single request exceeds Voyage's per-request token budget, and any one
  oversized document exceeds the per-input token cap — either way the whole request returns
  HTTP 400. This is the first wall; the run dies before retrieval.
- **`rerank`** — `pipeline/rerank.py:25` sends every candidate's **full text** to one
  `/rerank` call (`VoyageReranker.rerank`, `cloud.py:147`). Same failure mode.
- **`retrieve`** — `pipeline/retrieve.py:70` embeds all chunks of a document in one call; a large
  PDF produces hundreds of chunks per request.

`VoyageEmbed.embed` (`cloud.py:132`) and `VoyageReranker.rerank` (`cloud.py:147`) currently
contain no batching, no truncation, and no retry. The Ollama embedder already carries the boring
precedent — a character budget (`ollama_embed_chars=8000`, `config.py:45`) — but the Voyage
drivers never got the equivalent.

This is a **finding plus a fix-plan**, not a patch to build tonight. The cloud overlap
measurement it would unblock is **full-stack asymmetric** (Voyage embed + Voyage rerank + Haiku
LLM versus qwen3-embed + lexical rerank + Ollama LLM), so it can never be a clean sovereignty
claim regardless. Deferring it costs the demo nothing; rushing untested transport code onto the
relevance path costs auditability.

## What Changes

- **MODIFIED** `VoyageEmbed.embed` and `VoyageReranker.rerank` bound every outbound request to
  the provider's documented per-request limits, via two boring mechanisms:
  1. **Per-input truncation** — each input text is truncated to a configured character budget
     before sending, so no single oversized document can reject the whole request.
  2. **Batching** — an input list that exceeds a configured count limit *or* a cumulative
     character budget is split into sequential requests; results are concatenated in original
     input order. The `embed`/`rerank` contract (one vector/score per input, in input order) is
     unchanged, so **the pipeline's selection semantics are untouched**.
- **NEW** `Settings` fields (env-overridable, `ZEEF_` prefix), with conservative defaults that
  **MUST be verified against the current Voyage limits before implementation** (design D-LIMITS):
  `voyage_embed_chars`, `voyage_rerank_chars`, `voyage_batch_size`, `voyage_batch_chars`.
- **NEW** auditability — the applied limits are recorded in `run-manifest.json` (`params`), and
  any truncation that actually fires emits a `truncation` audit event (count truncated + max
  original length). Truncation becomes a visible, traceable variable, not a silent one.

## Capabilities

### Modified Capabilities
- `provider-profiles`: the cloud embedding and rerank providers now bound every request to the
  provider's per-request limits (truncation + batching) while preserving their observable
  `embed`/`rerank` contract. The applied limits are auditable. The sovereign profile and the
  selection logic are unchanged.

## Impact

- **Affected specs**: modified `provider-profiles` (cloud-driver request-limit contract).
- **Affected code (at implementation, not now)**: `src/zeef/drivers/cloud.py`
  (`VoyageEmbed.embed`, `VoyageReranker.rerank`, `_VoyageClient`); `src/zeef/config.py` (new
  `Settings` fields); `src/zeef/pipeline/run.py:177-189` (record limits in manifest `params`).
- **Callers — unchanged**: `relate`/`dedup.py:56`, `retrieve.py:65,70`, `rerank.py:25` all keep
  calling `embed`/`rerank` with the same signature; the fix lives entirely inside the drivers.
- **Selection semantics — unchanged**: same one-vector/one-score-per-input contract in input
  order; the selector (LLM relevance via `score.py:64`) is untouched.
- **Sovereign profile — untouched**: `HashingEmbed`, `OllamaEmbed`, `LexicalReranker` are not in
  scope.
- **Open decision blocks merge** (design D-RERANK-SPLIT): the rerank batching assumption — that
  Voyage returns an **absolute per-(query, document) relevance score independent of the other
  documents in the batch** — is **UNCONFIRMED**. It must be verified against the Voyage rerank
  docs before any rerank batching is implemented. If the score is batch-relative, rerank cannot
  be split and the plan for rerank changes (truncation-only within a single call).
- **Out of scope**: char-cap *parity* with the sovereign run (no cloud run is being scheduled, so
  there is nothing to compare yet — design D-CHARCAP records only the future reporting duty); the
  Claude LLM driver (`ClaudeLLM` already sends one prompt per call); retries/back-off on transient
  5xx (separate concern); any change to which stages call the cloud providers.

## Status

**Propose-only.** No code is written, nothing is committed to `main`, and the cloud run is not
executed. This is post-demo work, sequenced like the converge-ranking change.
