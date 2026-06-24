## 1. Config

- [x] 1.1 `config.py`: add `overlap_threshold` (< `near_dup_threshold`) and `summary_max_words` (100), in their own block
- [x] 1.2 Record both in the run-manifest params

## 2. Summarise (new capability)

- [x] 2.1 `pipeline/summarise.py`: `summarise(selected, providers, audit, *, max_words)` — one LLM call per selected document; cap at `max_words`; set `metadata["summary"]`; log prompt/model/location
- [x] 2.2 Skip entirely under `--no-llm` (no call); audit a `skipped` event
- [x] 2.3 Distinct from `rationale` (content summary vs relevance motivation)

## 3. overlaps-with band (modified relate)

- [x] 3.1 `pipeline/dedup.py`: in `link_near_duplicates`, emit `overlaps-with` for confirmed cosine in `[overlap_threshold, near_dup_threshold)`; `duplicate-of` stays at/above near-dup; evidence = the cosine
- [x] 3.2 `relate.py`: thread `overlap_threshold` through (default constant); count overlaps in the complete event

## 4. Export (modified)

- [x] 4.1 `export.py`: `write_inventory(..., include_summary)` — build the header with/without the `summary` column; assert on column name in tests, not index

## 5. Wiring (additive)

- [x] 5.1 `run.py`: run the `summarise` stage after `select` and after `topics`, before `export`, in the timer; pass `include_summary = not providers.no_llm` to `write_inventory`; thread `overlap_threshold`/`summary_max_words`; add both to the manifest params
- [x] 5.2 `cli.py`: pass `settings.overlap_threshold` and `settings.summary_max_words` (additive)

## 6. Test-hygiene fix

- [x] 6.1 `tests/test_cloud_auth.py`: make the `anthropic` import lazy/guarded (`pytest.importorskip` in the fixture) so the suite collects without `--extra cloud` and the cloud-only tests skip when the dep is absent

## 7. Tests

- [x] 7.1 `test_summarise.py` / `test_export.py`: with an LLM → `summary` column present + populated + prompt logged
- [x] 7.2 Under `--no-llm` → `summary` column **absent** (assert absence, not empty cell) and spy-LLM calls == []
- [x] 7.3 `test_dedup.py` (hinging pair): one pair just below near-dup → `overlaps-with`; one at/above → `duplicate-of`
- [x] 7.4 `openspec validate output-hygiene --strict`
- [x] 7.5 `uv run pytest` **with** `--extra cloud` green; **without** it collects cleanly and skips the cloud test; `ruff` clean; ≤200-line check

## 8. Docs & changelog

- [x] 8.1 README + de-pijplijn: summarise stage, conditional summary column, `overlaps-with` relation
- [x] 8.2 `CHANGELOG.md`: dated entry
