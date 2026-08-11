## Why

The Woo (Wet open overheid) process has a painful middle step: after source systems
are searched (phase 1) a department is left with ~1.000 semi-relevant documents that
must be narrowed to a core-relevant selection (~100) before redaction (phase 3). Today
this convergence is done by hand — slow, inconsistent, and hard to account for. There is
no open-source tool for it, even though the publication/search end of the chain
(OpenWoo / Common Ground: OpenConnector, OpenRegister, OpenCatalogi) is well covered.

`zeef` fills that gap: the missing open-source link *upstream* of the OpenWoo chain. It
borrows the recall-oriented method from e-discovery / TAR (technology-assisted review)
instead of inventing relevance ranking from scratch. The immediate driver is the Woo/ECP
technical exploration on **26 June 2026**, where the tool must run on a supplied dataset
and a refined search question and produce a defensible, fully traceable selection.

## What Changes

This is change #1: a working CLI MVP that runs the full convergence on a local folder:

```
zeef converge ./docs --query "..." --profile sovereign --target 100
```

- **NEW** `Document` canonical data model (pydantic v2) — every input file, regardless of
  format, is normalized to this single model. The spine of the whole pipeline.
- **NEW** Pluggable ingest loaders for `.eml`/`.msg` (headers preserved) and digital PDF,
  behind a `Loader` protocol.
- **NEW** Relate stage: mail-thread reconstruction from headers
  (`Message-ID`/`In-Reply-To`/`References`) and deterministic near-duplicate detection
  (MinHash/SimHash + embedding cosine), recorded as typed `Relation`s.
- **NEW** Scope-filter stage: rules-first exclusion of out-of-scope material, LLM only for
  genuine edge cases. Every exclusion gets a human-readable `decision_reason`.
- **NEW** Embed → Retrieve → Rerank pipeline against the refined query (vector first,
  optional BM25 hybrid; cross-encoder / LLM reranker for precision).
- **NEW** Configurable selection with three cutoff modes (`--top-n`, `--threshold`,
  `--target`) and an explicit, tunable recall bias (when in doubt, include).
- **NEW** Two provider profiles selected with `--profile`: `cloud` (top-quality, Claude
  API + hosted embeddings/rerank) and `sovereign` (fully local/air-gapped, Qwen3 via
  Ollama/vLLM). Plus a `--no-llm` flag that skips all generative steps. Same pipeline,
  only the drivers differ — switching profiles requires **no code change**.
- **NEW** JSONL audit-trail: every stage writes structured events (queries run, sub-selections,
  how relevance was determined, which model, **where it ran** local/cloud, and for LLM steps
  the exact prompt). Both the selected core and the excluded rest are fully reconstructable
  from the log. This is the differentiator.
- **NEW** Export: `inventory.xlsx` (id, score, category, summary, reason), `relations.json`
  (relation graph), and `audit.jsonl`.

## Capabilities

### New Capabilities
- `document-model`: the canonical `Document`/`Chunk`/`Relation` model and content-addressed id; the normalization contract every stage relies on.
- `ingest`: format-robust loaders (`.eml`/`.msg`, digital PDF) behind a `Loader` protocol, producing normalized `Document`s.
- `relate`: deterministic mail-thread reconstruction and near-duplicate detection, recorded as typed relations.
- `scope-filter`: rules-first out-of-scope exclusion with an LLM fallback for edge cases, each with a `decision_reason`.
- `retrieve-rerank`: chunk + embed, first-pass retrieval against the refined query, and a precision rerank pass.
- `select`: three configurable cutoff modes (`top-n`, `threshold`, `target`) with an explicit recall bias.
- `provider-profiles`: the `cloud`/`sovereign` profile abstraction over LLM/embedding/reranker providers, plus `--no-llm`.
- `audit-trail`: append-only JSONL event log making every selection and exclusion reproducible and traceable.
- `export`: Excel inventory, relations graph, and audit-log outputs.
- `cli`: the `zeef converge` Typer command wiring the pipeline together.

### Modified Capabilities
<!-- None — this is the first change; no existing specs to modify. -->

## Impact

- **New project**: Python 3.12+, `uv`-managed, pydantic v2, `typer` + `rich`. New repository,
  no existing code affected.
- **Dependencies**: pydantic, typer, rich, openpyxl (Excel), a PDF text extractor, an `.eml`/`.msg`
  parser, MinHash/SimHash library, embedding/rerank/LLM client libs (profile-dependent;
  `sovereign` talks to a local Ollama/vLLM, `cloud` to the Claude API + hosted embeddings).
- **No network in `sovereign` mode** (default-deny egress); `cloud` requires egress and is only
  usable where the environment permits it.
- **Out of scope for change #1** (planned follow-up changes): scanned-PDF/OCR + VL-reranker
  driver; clustering + summarization + highlighting (enrich); web UI; connectors to
  M365/DMS/case-management systems; redaction (phase 3).
