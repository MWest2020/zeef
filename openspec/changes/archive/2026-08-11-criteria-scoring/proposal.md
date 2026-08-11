## Why

Change #1 gave `zeef` a working, fully-deterministic convergence pipeline. But the
relevance signal that decides the core selection is still thin and hard to defend:

- A run takes a single refined query string. *What actually counts as relevant* is never
  made explicit, so a reviewer cannot inspect — or contest — the relevance definition.
- The score that drives the top-X (`final`) is the lexical reranker score in `sovereign`.
  It is reproducible, but it carries **no rationale**: the inventory says "selected because
  final=0.83 ≥ cutoff", not *why* the document matters.
- The only LLM judgement today is the scope-filter's binary RELEVANT/NIET-RELEVANT on edge
  cases — no graded relevance, no explanation.

For the Woo/ECP exploration (26 June 2026) the differentiator is **defensible, explainable**
selection. A jury (and an auditor) wants to see the relevance criteria written down, and a
per-document motivation for why it made — or missed — the core. That is exactly where an LLM
earns its place: judgement under linguistic ambiguity with no mechanical ground truth, where
a rationale raises defensibility.

## What Changes

Change #2 adds the two LLM touchpoints the method needs, while keeping the middle of the
pipeline deterministic. The rule for the format: **LLM only for judgement under linguistic
ambiguity without mechanical ground truth, and only where a rationale raises defensibility**
— criteria, borderline scoring, (later) categorisation and summarisation. Everything with a
mechanical ground truth (threads, duplicates, rule-based exclusion, chunking, vector/lexical
retrieval) stays deterministic.

- **NEW** Criteria-articulation stage (the *begin*): one LLM call turns the refined query into
  a small, explicit, named set of relevance criteria (label + description). This is the
  written-down relevance definition a reviewer can read and contest. Logged with the exact
  prompt and exported as `criteria.json`. Under `--no-llm` it degrades to a single
  deterministic criterion equal to the raw query, so the pipeline still runs air-gapped.
- **NEW** LLM relevance-scoring stage (the *eind*): for the top-K reranked candidates the LLM
  scores each document against the articulated criteria (0–100, normalised to `llm_relevance`)
  **and** produces a one-line rationale ("scoort hoog: bevat publicatie- én
  geheimhoudingsclausule tussen de genoemde partijen"). The LLM relevance score becomes the
  `final` score that drives the top-X; the deterministic rerank now serves as the cheap
  pre-trim that bounds how many documents reach the LLM. Each score + rationale is logged with
  its prompt, model and location.
- **MODIFIED** `final` score: when LLM scoring runs, `final = llm_relevance`; candidates
  outside the scored top-K are demoted out of contention (recorded, not silent). Under
  `--no-llm` `final` stays the rerank score — change #1 behaviour is preserved exactly.
- **MODIFIED** Export: `inventory.xlsx` gains a **motivatie** column (the per-document
  rationale); a new `criteria.json` artifact records the articulated relevance criteria.
- **MODIFIED** CLI: `--score-top-k N` bounds how many reranked candidates are LLM-scored
  (default from settings); the summary reports the criteria count and how many docs were scored.

## Capabilities

### New Capabilities
- `criteria`: articulate an explicit, named relevance-criteria set from the refined query (LLM),
  with a deterministic raw-query fallback under `--no-llm`; logged and exported as `criteria.json`.

### Modified Capabilities
- `retrieve-rerank`: the final selection score is the LLM relevance score against the criteria
  (with a per-document rationale) when an LLM is available; rerank becomes the bounded pre-trim.
- `export`: inventory gains a `motivatie` column; a `criteria.json` artifact is written.

## Impact

- **Affected specs**: new `criteria`; modified `retrieve-rerank`, `export` (and the `cli`
  surface via `--score-top-k`).
- **Affected code**: `models.py` (`Criterion`/`Criteria` + `Document.rationale`), new
  `pipeline/criteria.py` and `pipeline/score.py`, `pipeline/run.py` wiring, `export.py`,
  `config.py` (`llm_score_top_k`), `cli.py`.
- **No new dependencies**: scoring and articulation reuse the existing `LLMProvider.complete`
  contract — no protocol change, no new client libraries.
- **Determinism / sovereignty preserved**: `--no-llm` remains fully deterministic and
  air-gapped; LLM steps stay temperature-0 where the provider allows and always leave a prompt
  in the audit-log.
- **Out of scope (follow-up)**: categorisation / sub-topic clustering, summarisation and
  highlighting (the `enrich` stage); using criteria to expand the retrieval query; OCR/VL paths.
