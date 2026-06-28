## 1. Embed contract

- [x] 1.1 Add optional keyword `progress: Callable[[int, int], None] | None = None` to `EmbeddingProvider.embed` in `protocols.py`
- [x] 1.2 `OllamaEmbed.embed` (`drivers/ollama.py`): call `progress(i, len(texts))` per text in the loop, guarded by `if progress is not None`
- [x] 1.3 `HashingEmbed.embed` (`drivers/local.py`): same per-text call
- [x] 1.4 `VoyageEmbed.embed` (`drivers/voyage.py`): call `progress(cumulative, len(texts))` after each batch

## 2. Thread progress into relate

- [x] 2.1 `link_near_duplicates` (`pipeline/dedup.py`): add `progress=None` param, pass to `embed.embed([...], progress=progress)`
- [x] 2.2 `relate` (`pipeline/relate.py`): add `progress=None` param, pass to `link_near_duplicates`
- [x] 2.3 `pipeline/run.py`: pass `progress=item_progress("relate")` to the relate stage (retrieve keeps its own counter, passes no embed-progress)
- [x] 2.4 `observe.py`: add `"relate": "embedded"` to `_PROGRESS_VERB`

## 3. Tests

- [x] 3.1 Unit test: `HashingEmbed.embed(texts, progress=spy)` fires per text, last call `(N, N)`, vectors unchanged
- [x] 3.2 Unit test: `embed(progress=None)` is a no-op (no error, same output)
- [x] 3.3 Unit test: `relate(docs, HashingEmbed(), audit, progress=spy)` fires (corpus embedded for near-dup)
- [x] 3.4 Regression: pipeline observe on vs off → identical selection/decisions (extends existing observe test)

## 4. Docs & changelog

- [x] 4.1 README `--observe`: note that `relate` now reports progress too (the last silent stage)
- [x] 4.2 Dated `CHANGELOG.md` entry (what, why, files, test result)

## 5. Verify

- [x] 5.1 `ruff` + offline suite green; all files ≤200 lines
- [x] 5.2 Smoke on fixture corpus: `--observe` shows `relate: embedded N/total`; no `relate:` lines without `--observe`
