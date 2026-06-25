## Why

`discover` answers *what is in this corpus* without a query — clustering → a landkaart. That is a
discovery aid, **not** the BZK/ECP deliverable. The deliverable is the other branch: **~1000
documents + one refined query → a documented, reproducible top-100 on relevance.** That branch
(`converge`) exists as an MVP, but its selection signal has drifted and is no longer
one-sentence-defensible:

- Change #1 selected on a vector first-pass + reranker score; change #2 then made the **LLM
  relevance score** the cutoff driver. A jury/auditor asking "why is this document in the
  top-100, and that one not?" gets an answer that depends on an LLM judgement and a multi-stage
  score, not a single auditable rule.
- Worse, the current code has a **hidden recall-gate**: `rerank.py` overwrites `final` with the
  rerank/BM25 score and `score.py` demotes every non-top-K candidate to `final = 0.0`. So only the
  top-K rerank survivors can be selected and the passage cosine never drives the cut — BM25
  excludes documents *before* relevance matters. That is precisely the "miss relevant documents"
  failure the exploration must avoid.
- The clustering machinery (built for `discover`) is tempting to reuse as a *selector* — pick the
  documents in the on-topic clusters. That is the wrong tool: cluster membership is about *theme*,
  not *relevance to the query*, and using it to select would silently drop query-relevant
  documents that happen to land in "Overig".
- "Out of scope" (a forwarded mail, a calendar invite) and "off-theme" (a different subject) get
  conflated, so the exclusion log can't be read cleanly.

This change **locks the converge architecture** so every selection decision is explainable in one
sentence and reproducible before anyone touches a UI.

## What Changes

The core rule: **selection is ranking against the query, not clustering.** Clustering is only
navigation *on* the already-fixed selection.

- **NEW** `relevance-ranking`: the relevance score of a document is the **cosine of its
  best-matching passage to the query** (the max cosine over its chunk embeddings) — recall-friendly,
  so the one decisive passage in a long PDF is not averaged away. It is set as the `final` score on
  **every** candidate, deterministic, computed with the sovereign embedding model; documents are
  sorted by it and the top-N is the selection. This is the single, auditable relevance rule, and it
  ranks the **full candidate set** — no earlier pass may gate which documents are eligible.
- **MODIFIED** `select`: the top-N is fixed by the relevance ranking **before any UI
  interaction** — one documented, reproducible selection, independent of what a user later clicks.
  Cluster membership never filters the ranking; recall-bias still applies only at the cutoff.
- **MODIFIED** `retrieve-rerank` (closes a verified recall-gate): today three stages decide `final`
  — `retrieve.py` records the passage cosine as `embed_sim` but **not** `final`, `rerank.py` writes
  `final = rerank`, and `score.py` writes `final = llm_relevance` for the top-K and **demotes the
  rest to `0.0`**. The net effect is that BM25/rerank gates recall before the cosine matters. This
  change rewires `final = the passage cosine on every candidate`; the rerank score and the LLM
  relevance score become **side-scores** (transparency/"why") that never write `final` and never
  demote. The blast radius spans **three** code sites (`retrieve.py`, `rerank.py`, `score.py`), not
  just one — mapped in Impact and design D22.
- **MODIFIED** `relate`: near-duplicates are detected on whole-document embeddings; duplicates are
  **not silently dropped** but kept visible as a `duplicate-of` relation. Because the representative
  is the highest-**ranked** member, the duplicate-collapse runs **after** ranking (the order is
  explicit); ties are broken by a **query-independent** stable key (ingestion order / source path),
  since exact duplicates share a content-addressed id and cannot be tie-broken by it.
- **MODIFIED** `scope-filter`: "buiten reikwijdte" is reframed as a separate **process-role axis** —
  doorstuurmail, agendaverzoek, procesmelding, eerdere mail in een thread, dubbeling — each marked
  out-of-scope with a logged reason. This is **not** a theme cluster, and "Overig" (theme) is never
  equated with "buiten reikwijdte" (role).
- **MODIFIED** `viewer-ui`: the converge report carries the **refined query in its meta**, shows per
  document its relevance score and the **"why"** (the contributing passage/terms), and clusters the
  top-100 (chunk-level) into deelonderwerpen as a choice-menu for the requester. It is a distinct
  artifact from the discover-report (which carries "zonder zoekvraag").
- **MODIFIED** `audit-trail`: a transparency log records which query/queries ran, how relevance was
  determined, which embedding model and where it ran (sovereign/Ollama profile), and the exact
  prompts when an LLM produced labels.

## Capabilities

### New Capabilities
- `relevance-ranking`: per-document relevance = cosine of the best-matching passage to the query
  (max over chunk embeddings), set as `final` on every candidate; deterministic ranking over the
  **full candidate set** is the sole selector; the **five** hard invariants (ranking fixed before
  UI; clustering never filters; role and theme are separate axes; no score-mixing; **no hidden
  recall-gate** — rerank/LLM scores are side-scores, never a filter).

### Modified Capabilities
- `select`: top-N fixed by the relevance ranking before any UI interaction; clustering never filters.
- `retrieve-rerank`: whole-doc cosine is the relevance signal; rerank/LLM-score is not the selector.
- `relate`: dedup on full-text embeddings; representative chosen, rest logged as relations.
- `scope-filter`: process-role out-of-scope axis, separate from theme.
- `viewer-ui`: query in the report meta; per-doc relevance score + "why"; top-100 clustered as a menu.
- `audit-trail`: the spelregels transparency log (queries, relevance method, model+location, prompts).

## Impact

- **Affected specs**: new `relevance-ranking`; modified `select`, `retrieve-rerank`, `relate`,
  `scope-filter`, `viewer-ui`, `audit-trail`.
- **Affected code (implementation, later)** — the `final`-flow rewire spans **three** sites:
  `pipeline/retrieve.py` (set `final` = the max-chunk passage cosine on every candidate),
  `pipeline/rerank.py` (stop writing `final`; keep `rerank` as a side-score), `pipeline/score.py`
  (stop writing `final`, **stop demoting to `0.0`**; keep `llm_relevance` + rationale as side
  outputs). Plus `pipeline/relate.py` (representative after ranking, query-independent tiebreak),
  `pipeline/scope_filter.py` (process-role tagging), `pipeline/select.py` (rank the full set → top-N),
  `export.py`/templates (query in meta, deterministic per-doc "why"), `pipeline/run.py`, `config.py`
  (menu-cluster params scaled to ~100, independent of the discover defaults).
- **No new dependencies**: reuses the existing `EmbeddingProvider` and the `topic-clustering`
  machinery for the report menu; no new model client.
- **Determinism / sovereignty preserved**: the selector is fully deterministic and air-gapped; the
  same corpus + query + parameters reproduce the identical top-100. LLM use (criteria, labels,
  rationale) is enrichment only and always leaves a prompt in the audit-log.
- **Reframes change #2**: the LLM relevance score is no longer the cutoff driver but the
  per-document "why" on the selected set — flagged for review (see design D14).
- **Out of scope (this change)**: a cross-encoder precision rerank as the selector; query
  expansion/rewriting; whole-document relevance (recorded as the rejected alternative, see D15); the
  LLM "why" gloss (deterministic anchor now; gloss is a later nice-to-have, D23); OCR/VL paths; the
  implementation itself (this is propose-only).
