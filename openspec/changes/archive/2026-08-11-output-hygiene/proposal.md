## Why

Two leftover rough edges read as sloppy to an auditor, plus one named nice-to-have from the
criteria:

- The `summary` column exists in `inventory.xlsx` but is **never populated** — a "summary" header
  over empty cells looks worse than no column at all. The criteria list "summarise the document
  content in at most 100 words per document" as a nice-to-have.
- `overlaps-with` is declared in the `RelationKind` literal but is **never emitted** — a dead
  contract. The criteria explicitly name "overlapping text" as a relation to surface.

Separately, a parked test-hygiene bug: `tests/test_cloud_auth.py` imports `anthropic` at module
level, so the whole test suite fails to **collect** without the optional `cloud` dependency
installed. The air-gapped default should be testable without the cloud extra.

## What Changes

- **NEW** Per-document content summary (≤100 words, LLM) for the selected core, populating the
  `summary` column. The summary describes *what the document says* — distinct from the existing
  `rationale` (*why it scores*); both columns coexist. One LLM call per selected document, after
  `select` and after `topics`, logged with the exact prompt, model and location. Under `--no-llm`
  no summary is produced, no LLM call is made, and the `summary` column is **omitted** from
  `inventory.xlsx` — never an empty column.
- **MODIFIED** `relate`: emit `overlaps-with` for meaningful partial overlap — a pairwise
  similarity in the band below the duplicate threshold and at or above a configured overlap
  threshold (reusing the cosine already computed for near-duplicate confirmation). At or above the
  duplicate threshold the pair stays `duplicate-of`. Evidence is the cosine value.
- **MODIFIED** Export: the `summary` column is present and populated when summaries were produced,
  and omitted under `--no-llm`.
- **FIX** `tests/test_cloud_auth.py`: lazy/guarded `anthropic` import so the suite collects without
  the `cloud` extra and the cloud-only tests skip when the dependency is absent.

## Capabilities

### New Capabilities
- `summarise`: produce a ≤100-word content summary per selected document with the LLM; under
  `--no-llm` no summary and no LLM call.

### Modified Capabilities
- `relate`: emit `overlaps-with` relations for meaningful partial text overlap below the duplicate
  threshold.
- `export`: the `summary` column is populated when an LLM is available and omitted under `--no-llm`.

## Impact

- **Affected specs**: new `summarise`; modified `relate`, `export`.
- **Affected code**: new `pipeline/summarise.py`; `pipeline/dedup.py` (+`relate.py`) for the
  `overlaps-with` band; `export.py` (conditional `summary` column); `pipeline/run.py` (summarise
  stage after select+topics; thread `overlap_threshold`/`summary_max_words`; manifest params — all
  additive); `config.py` (`overlap_threshold`, `summary_max_words`); `cli.py` (pass the settings —
  additive); `tests/test_cloud_auth.py` (lazy import).
- **No new dependencies**: summarisation reuses `LLMProvider.complete`; the overlap band reuses the
  existing embedding cosine.
- **Determinism / sovereignty preserved**: `overlaps-with` is deterministic; the summary is the only
  generative addition (temperature-0 where the provider allows, prompt logged). `--no-llm` stays
  fully air-gapped and drops the `summary` column.
- **Out of scope (follow-up)**: the viewer that renders summaries and the relation graph
  (`viewer-ui`, change #4).
