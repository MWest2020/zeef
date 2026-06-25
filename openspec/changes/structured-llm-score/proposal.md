## Why

The LLM relevance-scoring stage (`src/zeef/pipeline/score.py`) extracts the score and rationale
from free-text by regex: `_SCORE_RE` (`score\s*[:=]?\s*(\d{1,3})`) and `_MOTIVE_RE`
(`motivatie\s*[:=]?\s*(.+)`). The prompt asks the model to emit `SCORE:` / `MOTIVATIE:` lines and
we scrape them back. This is brittle on the very axis the method sells as its differentiator —
defensible, explainable scoring:

- A model that phrases the number differently, adds prose, or localises the label drops to the
  score-0 fallback even when it gave a perfectly good judgement.
- Backends that support structured output (Claude tool-use, Ollama `format=json`) can *guarantee*
  a parseable shape; throwing that away to scrape text is strictly worse where it is available.

The fix is to use structured output where the backend reliably supports it, and keep the regex as
the explicit fallback for backends that do not. This change only swaps the **parse path** for the
LLM score; it does not touch the selection.

> **Apply dependency (hard order):** the `final`/demotion semantics of `score.py` are **superseded
> by `converge-ranking`**, which makes the deterministic passage cosine the sole selector and demotes
> the LLM score to a side-score ("why"). This change therefore **MUST apply after `converge-ranking`**.
> Where this proposal says the score maps to `llm_relevance`/`final` and keeps "top-K demotion" (a
> snapshot of today's behaviour), read that as the *pre-converge-ranking* state: once
> `converge-ranking` applies, `score.py` writes only `llm_relevance` + `rationale` and neither writes
> `final` nor demotes. Do not optimise the number that no longer selects.

## What Changes

- **MODIFIED** `pipeline/score.py` prefers structured output when the active LLM backend supports
  it: the model returns `{score: 0-100, motivatie: string}` against a fixed schema, mapped to
  `llm_relevance`/`final` (÷100, 0..1) and `rationale` exactly as today. Regex parsing of free
  text remains as the fallback path, unchanged.
- **NEW** optional, additive capability on the LLM drivers: `complete_json(prompt, schema, *,
  system) -> dict | None`. `LLMProvider.complete` is **not** touched. A backend advertises support
  via a `runtime_checkable` `StructuredLLMProvider` protocol (the capability is explicit and
  inspectable, not hidden behind `hasattr` dispatch).
- **MODIFIED** `drivers/cloud.py` (`ClaudeLLM`): implements `complete_json` via Claude tool-use
  with a forced `input_schema` (temperature 0). Wired structurally; not live-tested (no keys,
  egress unconfirmed — existing open question Q3).
- **MODIFIED** `drivers/ollama.py` (`OllamaLLM`): implements `complete_json` via `format` (JSON
  schema) on `/api/generate`.
- **MODIFIED** audit trail: the JSON-path score event additionally records the **schema** and the
  **raw structured response**, so the structured path is no thinner in the audit trail than the
  regex path it replaces.
- **MODIFIED** degradation: three explicit tiers — structured JSON when supported and valid →
  regex on free text → score-0 with the raw answer as rationale. Never crashes; never harder to
  parse than today.

## Capabilities

### Modified Capabilities
- `retrieve-rerank`: LLM relevance scoring uses guaranteed structured output (score + rationale)
  where the backend supports it, with the existing regex parsing as an explicit, tested fallback.
  Score semantics and the `--no-llm` skip are unchanged.

## Impact

- **Affected specs**: modified `retrieve-rerank` (LLM relevance scoring output + degradation +
  audit detail).
- **Affected code**: `pipeline/score.py` (prompt selection, `complete_json` use, three-tier
  parse, richer audit event); `protocols.py` (add `StructuredLLMProvider`; `LLMProvider`
  unchanged); `drivers/cloud.py` and `drivers/ollama.py` (add `complete_json`); possibly
  `config.py` (a flag only if a per-backend opt-out is wanted — default on where supported).
- **`LLMProvider.complete` — untouched.** The other `complete()` callers (`criteria.py`,
  `summarise.py`, `scope_filter.py`, `topic_labels.py`) are not modified by this change.
- **`NullLLM` (config.py)** does not implement `complete_json`; under `--no-llm` the score stage
  skips entirely (`score.py:48`) so it is never reached.
- **`profiles.py` — no change**: the structured capability lives on the driver; profile resolution
  already constructs the right driver.
- **Tests touched**: `tests/test_score.py`. The existing `FakeLLM` exposes only `complete`, so the
  current tests keep exercising the regex fallback for free (it is not a `StructuredLLMProvider`).
  A new `FakeLLM` with `complete_json` covers the JSON path; the unparseable→0.0 route is asserted
  on both paths.
- **Determinism / sovereignty preserved**: structured calls stay temperature 0; `--no-llm` remains
  fully deterministic and air-gapped; every call still logs its exact prompt.
- **Merge-safety**: touches `pipeline/score.py`, `protocols.py`, `drivers/cloud.py`,
  `drivers/ollama.py`, `config.py`, `test_score.py` — fully disjoint from `bm25-reuse`. The only
  shared file is `CHANGELOG.md` (append-only).
- **Out of scope**: structured output for the other LLM stages (criteria, summarise, scope-filter,
  topic-labels); live cloud testing; changing the score range or the selection logic.
