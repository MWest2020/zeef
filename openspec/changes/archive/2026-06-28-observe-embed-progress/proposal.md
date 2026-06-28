## Why

`--observe` renders one panel per stage *after* the stage finishes, by reading the
audit events that stage wrote. The retrieve stage embeds every candidate in a single
loop and writes its audit event only when the whole loop is done. On a large corpus
with a remote/slow embedder (e.g. Ollama, ~1000 docs) this is the longest stage and it
emits nothing while it runs — the terminal and any redirected observe log sit silent for
minutes, so the run looks frozen and cannot be followed live. Following a run live is the
entire point of `--observe`; without progress during the slowest stage the feature does
not deliver it.

## What Changes

- The embed loop in `pipeline/retrieve.py` surfaces incremental progress
  (e.g. `retrieve: embedded 200/868`) to the console while it runs, at a readable
  interval (not per-document spam), so it is visible in the terminal and in a redirected
  observe log (`tail`-friendly).
- The same treatment is applied to `embed_chunks` (the query-less discover route), which
  has the identical silent-loop problem.
- Progress output is a **no-op when `--observe`/`ZEEF_OBSERVE=1` is off** — default
  behaviour is unchanged.
- Progress is **purely cosmetic**: it does not write audit events, does not change
  ranking, selection, or any artifact. Re-running with and without `--observe` produces
  byte-identical outputs except for the terminal stream.
- No new dependency: reuse the existing `rich` console already used by `StageObserver`.

## Capabilities

### New Capabilities
- `observe`: live per-stage terminal observability for a run (`--observe` /
  `ZEEF_OBSERVE=1`). Establishes the existing per-stage panel behaviour as a spec and
  adds the new requirement that long-running stages report incremental progress while
  they run.

### Modified Capabilities
<!-- None. retrieve-rerank ranking behaviour is unchanged; only an observability side-channel is added. -->

## Impact

- Code: `src/zeef/pipeline/retrieve.py` (`retrieve`, `embed_chunks`), a small progress
  helper (in `observe.py` or alongside it), and the wiring in `pipeline/run.py` that
  passes an observe-aware progress callback into retrieve.
- Behaviour: terminal/log output only; no change to `audit.jsonl`, `inventory.xlsx`,
  `run-manifest.json`, or any selection result.
- Tests: a unit test asserting the callback fires N times for N candidates and is a
  no-op (no console writes) when observe is disabled.
- Docs: README `--observe` section gains a line that the embed stage reports progress.
