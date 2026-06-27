## 1. Progress helper

- [ ] 1.1 Add a progress-callback factory bound to the observer's console (e.g. `make_progress(console, stage)` in `observe.py`, or `StageObserver.progress_for(stage)`) returning a callable `(done, total) -> None` that prints a dim `  {stage}: embedded {done}/{total}` line
- [ ] 1.2 Compute the interval inside the callback so updates are bounded (~20 per stage): emit when `done % max(1, total // 20) == 0` and always on the final document

## 2. Wire progress into the embed loops

- [ ] 2.1 Add a keyword-only `progress: Callable[[int, int], None] | None = None` parameter to `retrieve()` in `pipeline/retrieve.py`; call it inside the per-candidate loop, guarded by `if progress is not None`
- [ ] 2.2 Add the same `progress` parameter to `embed_chunks()` and call it in its loop (discover route)
- [ ] 2.3 In `pipeline/run.py`, build the callback from the active observer only when observation is enabled and pass it to `retrieve()`/`embed_chunks()`; pass `None` otherwise so the loops are a true no-op

## 3. Tests

- [ ] 3.1 Unit test: with a stub `progress` spy and N candidates, assert the callback fires (bounded count, last call is `(N, N)`) and final scores are unchanged
- [ ] 3.2 Unit test: with `progress=None` the loop runs and writes nothing to the console (no-op path)
- [ ] 3.3 Regression test: run the pipeline with observation on and off over a small fixture corpus; assert `audit.jsonl` and the selection are identical between the two

## 4. Docs & changelog

- [ ] 4.1 Update the README `--observe` section: note that the embed/retrieve stage reports incremental progress while it runs
- [ ] 4.2 Add a dated `CHANGELOG.md` entry (what changed, why, files touched, test result)

## 5. Verify

- [ ] 5.1 Run `ruff` and the offline test suite; confirm green
- [ ] 5.2 Manual smoke: `zeef converge <small corpus> --profile sovereign --no-llm --observe` and confirm `retrieve: embedded N/total` lines appear; repeat without `--observe` and confirm none appear
