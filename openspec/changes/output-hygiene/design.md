## Context

Change #1 (validity-gate) and #2 (topic-clustering) are merged. This change cleans up two
output-shape issues the criteria touch on — an always-empty `summary` column and an unused
`overlaps-with` relation kind — plus a parked test-collection bug. It follows the project's D9 rule:
the LLM only for judgement under linguistic ambiguity where a written artefact raises defensibility
(here: a content summary); everything mechanical (the overlap band) stays deterministic.

## Goals / Non-Goals

**Goals**
- A `summary` column that is populated (LLM) or absent (`--no-llm`) — never an empty column.
- A real `overlaps-with` relation for partial overlap, so the `RelationKind` contract is honoured.
- The test suite collects without the optional `cloud` dependency.

**Non-Goals**
- Rendering summaries / relations (that is `viewer-ui`, change #4).
- Summarising excluded documents (only the selected core is summarised — no wasted calls).
- A new similarity signal — the overlap band reuses the embedding cosine already computed.

## Decisions

### H1 — No empty columns
A column exists only when it carries data. With an LLM, `summary` is populated. Under `--no-llm` the
column is omitted. So `write_inventory` takes an `include_summary` flag (the pipeline sets it from
whether an LLM ran); the inventory header is built from it. This removes the "summary header over
empty cells" smell rather than papering over it with blanks.

### H2 — Summary ≠ rationale
The existing `rationale` (the per-document relevance *motivation* — why it scores) stays untouched.
`summary` is a content summary (what the document says). It is a separate LLM call, capped at
`summary_max_words`, and runs only over the selected core (after `select` and after `topics`), never
over excluded documents.

### H3 — `overlaps-with` as a band, not a duplicate
Dedup marks `duplicate-of` at or above the near-duplicate threshold. `overlaps-with` fills the gap
just below it: a confirmed cosine in `[overlap_threshold, near_dup_threshold)` is meaningful partial
overlap without being a duplicate. This is not a new signal — it is a second threshold on the cosine
already computed for the MinHash candidate pairs, so an overlap is only surfaced for pairs the
near-duplicate machinery already considers. Evidence is the cosine value. After this change every
`RelationKind` is actually emitted somewhere.

### H4 — Summary depends on the LLM, the column depends on the summary
The summarise stage skips entirely under `--no-llm` (no call, mirroring the score stage). Because no
summary is then produced, the export omits the column. The two facts are linked through one
condition (an LLM is available), keeping the behaviour easy to reason about and test.

### H5 — Test collection must not need the cloud extra
`tests/test_cloud_auth.py` imported `anthropic` at module scope, breaking collection of the whole
suite without `--extra cloud`. The import moves into the fixture via `pytest.importorskip`, so the
suite collects air-gapped and the cloud-only tests skip cleanly when the dependency is absent. The
tests that never touch `anthropic` (subscription key-pop, api-key-requires-key) keep running.

## Risks / Trade-offs

- **Summarisation cost.** One extra LLM call per selected document (~100). Mitigation: only the core,
  temperature-0, and it runs after `select` so never over the full ~1000.
- **Overlap-threshold tuning.** Too low surfaces noisy overlap edges. Mitigation: a conservative
  default, logged in the run-manifest, tunable on the real set.
- **Dynamic inventory columns.** Tests that key on a fixed column index would break. Mitigation:
  tests assert on column name, not index (already the convention from change #2).
- **Overlap recall is bounded by the MinHash candidate set.** A pair with band-level cosine but low
  shingle overlap is not a candidate and so not surfaced. Acceptable: `overlaps-with` reuses the
  existing near-duplicate candidate machinery by design; broadening candidate generation is out of
  scope.

## Migration Plan

Additive. The summarise stage runs after select/topics; under `--no-llm` it is a no-op and the
column is dropped, so air-gapped runs are unchanged except for the (now absent) empty column. The
`overlaps-with` band only adds relations for pairs already below the duplicate threshold — no
existing `duplicate-of` relation changes.
