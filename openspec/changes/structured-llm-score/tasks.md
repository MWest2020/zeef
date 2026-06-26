## 1. Capability protocol (`protocols.py`)

- [x] 1.1 Add `runtime_checkable` `StructuredLLMProvider` protocol with `name`, `location`, and
      `complete_json(prompt, schema, *, system) -> dict | None`
- [x] 1.2 Leave `LLMProvider` exactly as is (additive, separate protocol)

## 2. Driver support (additive `complete_json`)

- [x] 2.1 `drivers/ollama.py` `OllamaLLM.complete_json`: send the fixed schema via `format` on
      `/api/generate` (temperature 0); parse `response` as JSON; validate required fields; return
      `None` on miss/invalid → ruimere `num_predict`-ondergrens zodat de JSON niet wordt afgekapt
- [x] 2.2 `drivers/cloud.py` `ClaudeLLM.complete_json`: force a tool-use call with the schema as
      `input_schema` (temperature 0); return the tool input dict; return `None` on no tool call.
      Wired, not live-tested (Q3) → `_client()`-helper geëxtraheerd (dedup met `complete`)
- [x] 2.3 Confirm `NullLLM` is untouched and does **not** satisfy `StructuredLLMProvider`
      → test_capability_protocol_distinguishes_backends (complete-only ⇒ niet het protocol)

## 3. Scoring stage (`pipeline/score.py`)

- [x] 3.1 Define the fixed JSON schema (`score` 0-100, `motivatie` string; both required) → `_SCHEMA`
- [x] 3.2 Three-tier parse (D-DEGRADE): structured (`isinstance(llm, StructuredLLMProvider)`) →
      regex (`complete` + existing `_SCORE_RE`/`_MOTIVE_RE`) → score-0 with raw answer → `_judge`
- [x] 3.3 Map score → `llm_relevance` (clamp 0..100, ÷100) and `rationale` — identical semantics on
      every tier. **Reframe (converge-ranking):** score schrijft `final` NIET meer; `llm_relevance`
      is een side-score, `final` blijft de passage-cosine.
- [x] 3.4 Keep `_SCORE_RE`/`_MOTIVE_RE`/`_parse` as the fallback (do not delete)
- [x] 3.5 JSON-path audit event also records `schema` and `raw_structured` (D-AUDIT); regex path
      logs the free-text answer as today; both keep `prompt`/`model`/`location` + nieuwe `route`
- [x] 3.6 `--no-llm` skip and never-crash behaviour unchanged. **Reframe:** top-K demotion bestaat
      niet meer (verwijderd in converge-ranking); de stage demoveert niemand.
- [ ] 3.7 (optional) `config.py` per-backend opt-out flag to force the regex path → **bewust
      overgeslagen** (optioneel): de drie-tier fallback degradeert al veilig per call; een statische
      opt-out is nu niet nodig en zou een ongebruikte knop toevoegen. Te heroverwegen als een
      Ollama-deployment structureel onbetrouwbare JSON geeft.

## 4. Tests (`tests/test_score.py` + `tests/test_structured_score.py`)

- [x] 4.1 New JSON-path fake (implements `complete_json`): scoring sets relevance/rationale and the
      audit event carries `schema` + `raw_structured` → test_structured_path_sets_relevance_and_logs_schema
- [x] 4.2 Existing `complete`-only `FakeLLM` still drives the regex fallback (assert it is *not* a
      `StructuredLLMProvider`) — current test_score.py green for free
- [x] 4.3 `complete_json` returns `None`/invalid/raises → falls back to regex (assert regex path taken)
      → test_complete_json_none/invalid/raising_falls_back_to_regex
- [x] 4.4 Unparseable on both paths → `llm_relevance == 0.0`, raw answer kept (`final` onaangeroerd)
      → test_both_paths_unparseable_scores_zero_relevance
- [x] 4.5 `--no-llm` still skips (existing test unchanged) → test_no_llm_skips_and_keeps_cosine_final

## 5. Verify (isolated — change 2 only, after change 1 is archived)

- [x] 5.1 `uv run pytest` — full suite green (offline) → 148 passed, 1 skipped
- [x] 5.2 `uv run ruff check` clean on touched files
- [ ] 5.3 Sovereign smoke-run with Ollama up — confirm the JSON path runs end to end under a real
      model → **niet uitgevoerd** (vereist een draaiende Ollama + gewichten; de fallback-paden zijn
      met fakes gedekt). Te draaien wanneer een lokale Ollama beschikbaar is.
- [x] 5.4 `openspec validate structured-llm-score`
- [x] 5.5 Update `CHANGELOG.md` (dated entry: structured output + regex fallback, prompt/audit
      changes, files, tests)
