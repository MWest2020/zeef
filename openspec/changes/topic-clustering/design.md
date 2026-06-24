## Context

The selected core (~100) must be shown to the requester as a navigable menu of sub-topics. So the
stage runs on the selected set *after* `select`, not over the whole corpus. Embeddings already
exist from the retrieve stage — the grouping reuses an existing signal rather than computing a new
one. This change adds the grouping as its own stage, keeps the grouping deterministic, and confines
the LLM to labelling (consistent with the `criteria-scoring` D9 rule: LLM only for judgement under
linguistic ambiguity without mechanical ground truth, always logged).

## Goals / Non-Goals

**Goals**
- A reproducible two-level onderwerp/deelonderwerp grouping of the selected core.
- A `topics.json` artifact that is sufficient on its own to present the selection as a menu.
- Stop the inventory `category` column from misleadingly carrying the file type.

**Non-Goals**
- Re-deciding relevance or selection — this stage groups what `select` already chose.
- Multiple topic assignment per document (v1 is single assignment; see T4).
- Rendering the menu (that is `viewer-ui`).
- Per-document summarisation (that is `output-hygiene`).

## Decisions

### T1 — Cluster the core, not the corpus
The choice menu is about what the requester receives, so the stage runs on the selected set after
`select`, never over the full ~1000.

### T2 — Deterministic two-level grouping
Agglomerative hierarchical clustering (cosine distance, average linkage) over the document
embeddings; the dendrogram is cut at two heights → onderwerp (coarse) and deelonderwerp (fine,
nested within an onderwerp). Fixed linkage and fixed thresholds make it reproducible. The
thresholds (`onderwerp_distance`, `deelonderwerp_distance`) and `min_cluster_size` live in
`config.py` and are recorded in the run-manifest. The LLM never decides *which* documents belong
together.

### T3 — LLM labels only, with a deterministic fallback
Per cluster, one LLM call with representative snippets (the medoid plus its nearest members:
title + first lines) produces a short Dutch label; temperature-0, with the prompt, model and
location logged. Under `--no-llm` the label is built from the cluster's most distinctive terms
(TF-IDF of the cluster against the rest), marked `source: fallback`, and no LLM call is made.

### T4 — One onderwerp + one deelonderwerp per document (v1)
This resolves the open "multiple assignment" question conservatively. Single assignment keeps both
the menu and the audit unambiguous: each document appears in exactly one place in `topics.json` and
has one category cell. Multiple assignment is a follow-up.

### T5 — Deterministic handling of small clusters
Clusters below `min_cluster_size` collapse into a single deterministic **"Overig"** onderwerp so
the menu does not fragment into singletons. The collapse is recorded in the audit-log.

### T6 — Category rebind, nothing lost
`category` becomes `"<onderwerp> / <deelonderwerp>"`; the file type moves to its own `doc_type`
column. This fixes the misleading-label problem while preserving the data.

## Risks / Trade-offs

- **Cluster-count sensitivity.** The thresholds decide how many onderwerpen appear; too coarse is
  useless, too fine fragments. Mitigation: conservative defaults, both thresholds logged in the
  manifest and tunable once the real set is known; `min_cluster_size` + "Overig" bound the
  fragmentation.
- **Label drift.** A label can be slightly off. Low risk: labels are descriptive, not decisive
  (they move no document into or out of the selection), temperature-0, and the prompt is in the
  audit-log.
- **New dependency (`scipy`).** Standard but heavier; placed in the `sovereign` extra and imported
  only inside the stage so air-gapped `--no-llm` runs that skip clustering pay nothing at import
  time.

## Migration Plan

Additive. The stage runs only after `select`; existing behaviour up to and including selection is
unchanged. Under `--no-llm` the grouping still runs (deterministic) and labels fall back to terms —
no new air-gapped failure mode. The inventory `category` rebind plus the new `doc_type` column is
the only output-shape change; tests assert on column *name*, not index.

## Open Questions

- Final default values for `onderwerp_distance` / `deelonderwerp_distance` / `min_cluster_size` —
  guesses until the real PDF set is seen; conservative defaults shipped, all logged in the manifest.
- Whether multiple-assignment is worth it for the day, or single assignment (T4) is enough for the
  menu — deferred to follow-up.
