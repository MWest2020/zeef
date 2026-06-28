## Context

`observe-embed-progress` added per-item counters to `ingest` and `retrieve` by hooking the
Python loops in those stages. `relate` has no such loop: `link_near_duplicates` (dedup.py)
embeds the whole corpus in a single `embed.embed([...])` call, then loops MinHash candidate
pairs (cheap). The wall-clock is inside that one embed call — for Ollama, `embed()` itself
loops per text with one HTTP request each (`ollama.py`), which is where the time and the
occasional 500 live. So progress for `relate` must originate **inside the embedder**.

## Goals / Non-Goals

**Goals:**
- A live counter for the `relate` near-dup embedding under `--observe`.
- Mechanism general enough to serve any future big-batch embed, via the embedder itself.
- Zero behaviour change when off; no mutable driver state; results identical.

**Non-Goals:**
- Touching `retrieve`'s counter (it already counts per doc; it will NOT pass embed-progress, to
  avoid double reporting).
- Logging the embed-500 into the audit trail (separate concern; this change only makes the
  stage *followable*, not the 500 *auditable*).
- A progress bar / animation. Plain bounded lines, as established.

## Decisions

### Decision: optional `progress` keyword on `embed()`, threaded explicitly

`EmbeddingProvider.embed(texts, *, progress=None)`. The driver calls `progress(done, total)` as
it processes the list. The callback is passed `run.py → relate → link_near_duplicates →
embed.embed(progress=...)`.

*Why over alternatives:*
- *Mutable `progress` attribute on the driver, set/cleared around relate by the observer* —
  hidden state on a shared provider, easy to leave set; smells for "boring/auditable". Rejected.
- *Re-architect relate to embed in chunked sub-batches with a loop in the stage* — changes the
  embedding call pattern and risks performance/dedup behaviour. Rejected.
- Explicit optional param mirrors how `ingest`/`retrieve` already received `progress`, is a pure
  additive contract change (default `None` = today), and keeps the driver stateless. Chosen.

### Decision: drivers report at their natural granularity

Ollama and local `HashingEmbed` loop per text → call `progress(i, len(texts))` per text. Voyage
loops per batch → call `progress(cumulative, len(texts))` after each batch. The throttling to
~20 lines lives in `StageObserver.progress_for` (unchanged), so per-text calls are cheap and the
output stays bounded regardless of driver granularity.

### Decision: only `relate` passes embed-progress

`retrieve` already prints a per-doc counter; passing embed-progress there too would double up.
So `retrieve`'s `embed()` calls pass no `progress`. `observe.py` gains a `relate → "embedded"`
verb entry; the existing `item_progress("relate")` wiring in `run.py` produces the callback.

## Risks / Trade-offs

- [Protocol change ripples to all embedders] → Optional keyword with default `None`; every
  existing call site and the three drivers keep working unchanged. Covered by the offline suite.
- [Per-text callback overhead] → A function call + modulo per text; negligible against one HTTP
  embed per text. Throttling keeps console writes ~20/stage.
- [relate progress vs the completion panel ordering] → Same console, synchronous stage: progress
  lines then the panel, as with ingest/retrieve.
