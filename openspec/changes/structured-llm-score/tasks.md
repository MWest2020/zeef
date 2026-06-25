## 1. Capability protocol (`protocols.py`)

- [ ] 1.1 Add `runtime_checkable` `StructuredLLMProvider` protocol with `name`, `location`, and
      `complete_json(prompt, schema, *, system) -> dict | None`
- [ ] 1.2 Leave `LLMProvider` exactly as is (additive, separate protocol)

## 2. Driver support (additive `complete_json`)

- [ ] 2.1 `drivers/ollama.py` `OllamaLLM.complete_json`: send the fixed schema via `format` on
      `/api/generate` (temperature 0); parse `response` as JSON; validate required fields; return
      `None` on miss/invalid
- [ ] 2.2 `drivers/cloud.py` `ClaudeLLM.complete_json`: force a tool-use call with the schema as
      `input_schema` (temperature 0); return the tool input dict; return `None` on no tool call.
      Wired, not live-tested (Q3)
- [ ] 2.3 Confirm `NullLLM` is untouched and does **not** satisfy `StructuredLLMProvider`

## 3. Scoring stage (`pipeline/score.py`)

- [ ] 3.1 Define the fixed JSON schema (`score` 0-100, `motivatie` string; both required)
- [ ] 3.2 Three-tier parse (D-DEGRADE): structured (`isinstance(llm, StructuredLLMProvider)`) →
      regex (`complete` + existing `_SCORE_RE`/`_MOTIVE_RE`) → score-0 with raw answer
- [ ] 3.3 Map score → `llm_relevance`/`final` (clamp 0..100, ÷100) and `rationale` — identical
      semantics on every tier
- [ ] 3.4 Keep `_SCORE_RE`/`_MOTIVE_RE`/`_parse` as the fallback (do not delete)
- [ ] 3.5 JSON-path audit event also records `schema` and `raw_structured` (D-AUDIT); regex path
      logs the free-text answer as today; both keep `prompt`/`model`/`location`
- [ ] 3.6 `--no-llm` skip, top-K demotion, and never-crash behaviour unchanged
- [ ] 3.7 (optional) `config.py` per-backend opt-out flag to force the regex path; default
      structured-where-supported

## 4. Tests (`tests/test_score.py`)

- [ ] 4.1 New JSON-path fake (implements `complete_json`): scoring sets relevance/rationale/final
      and the audit event carries `schema` + `raw_structured`
- [ ] 4.2 Existing `complete`-only `FakeLLM` still drives the regex fallback (assert it is *not* a
      `StructuredLLMProvider`) — current tests stay green for free
- [ ] 4.3 `complete_json` returns `None`/invalid → falls back to regex (assert regex path taken)
- [ ] 4.4 Unparseable on both paths → `final == 0.0`, raw answer kept (assert on JSON and regex)
- [ ] 4.5 `--no-llm` still skips (existing test unchanged)

## 5. Verify (isolated — change 2 only, after change 1 is archived)

- [ ] 5.1 `uv run pytest` — full suite green (offline)
- [ ] 5.2 `uv run ruff check` clean on touched files
- [ ] 5.3 Sovereign smoke-run with Ollama up — confirm the JSON path runs end to end under a real
      model, falls back cleanly if the model's JSON is unreliable
- [ ] 5.4 `openspec validate structured-llm-score`
- [ ] 5.5 Update `CHANGELOG.md` (dated entry: structured output + regex fallback, prompt/audit
      changes, files, tests)
