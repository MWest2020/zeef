## 1. Progress helper

- [x] 1.1 Add a progress-callback factory bound to the observer's console (e.g. `make_progress(console, stage)` in `observe.py`, or `StageObserver.progress_for(stage)`) returning a callable `(done, total) -> None` that prints a dim `  {stage}: embedded {done}/{total}` line
- [x] 1.2 Compute the interval inside the callback so updates are bounded (~20 per stage): emit when `done % max(1, total // 20) == 0` and always on the final document

## 2. Wire progress into the embed loops

- [x] 2.1 Add a keyword-only `progress: Callable[[int, int], None] | None = None` parameter to `retrieve()` in `pipeline/retrieve.py`; call it inside the per-candidate loop, guarded by `if progress is not None`
- [x] 2.2 Add the same `progress` parameter to `embed_chunks()` and call it in its loop (discover route)
- [x] 2.3 In `pipeline/run.py`, build the callback from the active observer only when observation is enabled and pass it to `retrieve()`/`embed_chunks()`; pass `None` otherwise so the loops are a true no-op
- [x] 2.4 Add the same `progress` parameter to `ingest()` in `pipeline/ingest.py` (total = number of files); call it per file, and wire it from `run.py` (observer → `progress_for("ingest")`, else `None`)
- [x] 2.5 Enrich the criteria observe panel: in `observe_blocks.py` `_criteria`, read the `--no-llm` `fallback` event's `query` and show the first ~60 chars as INPUT (e.g. `zoekvraag: "Alle documenten over …"`), not the bare word "zoekvraag". Display-only; no audit/pipeline change

## 3. Tests

- [x] 3.1 Unit test: with a stub `progress` spy and N candidates, assert the callback fires (bounded count, last call is `(N, N)`) and final scores are unchanged
- [x] 3.2 Unit test: with `progress=None` the loop runs and writes nothing to the console (no-op path)
- [x] 3.3 Regression test: run the pipeline with observation on and off over a small fixture corpus; assert `audit.jsonl` and the selection are identical between the two
- [x] 3.4 Unit test: `_criteria` block shows a prefix of the query in the `--no-llm` fallback path (INPUT contains the query text, not just "zoekvraag")

## 4. Docs & changelog

- [x] 4.1 Update the README `--observe` section: note that the embed/retrieve stage reports incremental progress while it runs
- [x] 4.2 Add a dated `CHANGELOG.md` entry (what changed, why, files touched, test result)

## 5. Verify

- [x] 5.1 Run `ruff` and the offline test suite; confirm green
- [x] 5.2 Manual smoke on the fixture corpus: `zeef converge <fixture> --profile sovereign --no-llm --observe` and confirm all three are visible — ingest counter, criteria-panel INPUT with the query, and `retrieve: embedded N/total`; repeat without `--observe` and confirm none appear
