## Why

The previous change (`observe-embed-progress`) gave `ingest` and `retrieve` live counters,
but `relate` stayed silent. `relate` embeds the whole corpus for near-duplicate confirmation
in **one batch call** (`embed.embed([d.text for d in targets])` in `dedup.py`), so there is no
Python loop in the stage to count between — the slowness lives inside the embedder. On the BZK
corpus with Ollama this stage took 245s–2071s with no output, the last silent stretch under
`--observe`. The same single batch is also where the recurring embed-500/nulvector-fallback
fires, unseen until the stage ends.

## What Changes

- `EmbeddingProvider.embed` gains an **optional keyword `progress` callback** (`(done, total) ->
  None`, default `None`). The drivers call it as they work through the input list (Ollama and
  local per text; Voyage per batch). Default `None` → unchanged behaviour.
- The callback is threaded explicitly: `run.py` → `relate` → `link_near_duplicates` →
  `embed.embed(..., progress=...)`. Only the `relate` stage passes it (when `--observe` is on);
  `retrieve` keeps its existing per-doc counter and passes nothing.
- Result: under `--observe`, `relate` now prints `relate: embedded N/total` at a bounded
  interval (~20 lines), so the last silent embed stage becomes followable.
- No mutable driver state, no protocol behaviour change: `embed(texts)` still returns one vector
  per input in order. No-op when `--observe` is off; ranking/selection/artifacts unchanged.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `observe`: the "Live progress during long per-item stages" requirement extends to the
  `relate` near-duplicate embedding (currently lists only ingest/retrieve/embed_chunks).

## Impact

- Code: `protocols.py` (`embed` signature), drivers `ollama.py` / `local.py` / `voyage.py`
  (accept + call `progress`), `pipeline/dedup.py` (`link_near_duplicates`), `pipeline/relate.py`
  (`relate`), `pipeline/run.py` (wire relate progress), `observe.py` (`relate` verb).
- Behaviour: terminal/observe-log only; no change to `audit.jsonl` or any artifact.
- Tests: per-text `progress` fires for the local driver; `relate` reports progress; no-op when
  `progress=None`; observe on/off identical selection.
- Docs: README `--observe` note that `relate` now reports progress too.
