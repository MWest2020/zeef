## 1. Data model

- [x] 1.1 Add `Criterion{label, description}` and `Criteria{query, items, source}` pydantic models to `models.py`
- [x] 1.2 Add `Document.rationale: str = ""` (per-document relevance motivation, distinct from `decision_reason`)
- [x] 1.3 Export the new models from `models.__all__`

## 2. Criteria articulation (begin)

- [x] 2.1 `pipeline/criteria.py`: `articulate_criteria(query, providers, audit) -> Criteria` (one LLM call, 3–6 named criteria)
- [x] 2.2 Tolerant `LABEL: beschrijving` line parsing; empty/colon-less lines skipped
- [x] 2.3 Deterministic `--no-llm` fallback: single criterion = raw query, `source="fallback"`, no LLM call
- [x] 2.4 Audit event with the exact prompt, model and location (and the parsed criteria)

## 3. LLM relevance scoring (eind)

- [x] 3.1 `pipeline/score.py`: `score(candidates, criteria, providers, audit, query, *, top_k)` reusing `LLMProvider.complete`
- [x] 3.2 Two-line `SCORE:`/`MOTIVATIE:` prompt; tolerant parse, score-0 fallback keeps the raw answer (never crash)
- [x] 3.3 Set `scores["llm_relevance"]`, `scores["final"] = llm_relevance`, and `rationale` per scored document
- [x] 3.4 Demote candidates beyond top-K (`final = 0.0`) with a recorded reason; `top_k=0` scores all
- [x] 3.5 Skip entirely under `--no-llm` (final stays = rerank); log scored-vs-demoted counts
- [x] 3.6 Per-document audit event with the exact prompt, model and location

## 4. Wiring & config

- [x] 4.1 `config.py`: `llm_score_top_k: int = 250`
- [x] 4.2 `run.py`: run `criteria` first and `score` between `rerank` and `select`; thread `score_top_k`; carry `criteria` in `RunResult`
- [x] 4.3 `cli.py`: `--score-top-k` option; summary reports criteria count + docs scored
- [x] 4.4 `run-start` audit event records `score_top_k`

## 5. Export

- [x] 5.1 `export.py`: add trailing `motivatie` column to `inventory.xlsx` (carries `rationale`)
- [x] 5.2 `export.py`: `write_criteria(criteria, path)` → `criteria.json`; wire it into `run.py`
- [x] 5.3 Add `criteria.json` to the export audit event's file list

## 6. Tests

- [x] 6.1 `test_criteria.py`: LLM articulation parses named criteria + logs prompt; `--no-llm` fallback = single raw-query criterion, no call
- [x] 6.2 `test_score.py`: FakeLLM scoring sets `llm_relevance`/`final`/`rationale`; top-K demotes the rest; `--no-llm` skips (final unchanged); prompt logged
- [x] 6.3 `test_export.py`: `motivatie` column present and carries the rationale; `criteria.json` shape
- [x] 6.4 Full suite green, including the ≤200-line and air-gapped e2e checks (change #1 behaviour preserved under `--no-llm`)

## 7. Docs, presentation & changelog

- [x] 7.1 `docs/.../de-pijplijn.md`: add the criteria + scoring stages; update the stage table and the "what drives top-X" story
- [x] 7.2 `docs/.../architectuur.md`: record the D9 "LLM or not" rule and the criteria/scoring touchpoints
- [x] 7.3 README + `presentation/index.html`: reflect criteria-articulation + explainable scoring with rationale
- [x] 7.4 `CHANGELOG.md`: dated entry for change #2 (what, why, files, test result)
