## Context

`zeef` now has two branches over the same deterministic spine (ingest → validity → relate →
scope-filter → embed → … → export). `discover` (changes already shipped) clusters the whole valid
corpus into a query-less landkaart. `converge` (changes #1/#2) takes a refined query and produces a
core selection. The Woo/ECP deliverable is the **converge** result: ~1000 documents + one refined
query → a documented, reproducible top-100 on relevance.

The risk this change closes: the selection signal has become a multi-stage, partly-LLM score
(change #2 made `final = llm_relevance` the cutoff), and the powerful clustering machinery invites
using *theme membership* as a selector. Both make the top-100 harder to defend and entangle two
things that must stay separate — *relevance to the query* (an axis), *theme* (a navigation
grouping), and *process role* (a third axis). This change fixes one boring, auditable selector and
nails down the invariants.

## Goals / Non-Goals

**Goals:**
- One auditable relevance rule: a single cosine number per document against the query.
- A top-100 that is fixed by ranking and reproducible **before** any UI interaction.
- Keep theme (cluster) and process-role (out-of-scope) as two separate axes; never let either
  filter the ranking.
- Make duplicates visible as relations rather than silently dropped.
- Make the deliverable report self-evidently *about a query* (query in meta + per-doc "why").

**Non-Goals (this change):**
- A cross-encoder/LLM precision rerank as the selector (deferred; sovereign has no reranker model).
- Query expansion/rewriting (retrieval still uses the refined query verbatim).
- Changing the `discover` branch or its report.
- Implementation, embedding runs, or benchmarking — this is propose-only.

## Decisions

### D14 — The selector is a deterministic cosine ranking; change #2 is reframed
The selector is the deterministic cosine ranking defined in D15 — the cosine of the best-matching
passage to the query (max over chunk embeddings). Documents are sorted by it and the top-N is cut;
this is the **sole** selector. (D15 records the representation choice and why whole-document is the
rejected alternative; D14 only fixes the role of the LLM score.)

This **reframes change #2**: the LLM relevance score and rationale no longer drive the cutoff; they
become the per-document **"why"** on the already-selected set. Rationale: a jury/auditor must get a
one-sentence answer ("this document ranks #37 because its best-matching passage is cosine-closest to
the query"), reproducible without an LLM and identical on re-run. The LLM remains valuable for
explanation, not for deciding membership.

### D15 — Document relevance representation: max-chunk (DEFAULT) vs whole-doc (RECORD BOTH)
Two defensible representations of "how relevant is this document to the query":
- **Max chunk-to-query similarity** (chosen default). Embed the document's chunks and take the
  highest chunk cosine to the query as the document's relevance. The exploration runs on ~1000
  documents including long PDFs and is rewarded for *not missing*; relevance is "does a passage
  match the query", so the decisive passage must not be averaged away. This is also already the
  code's behaviour (`retrieve.py` computes `max(cosine(query, chunk))`). One-sentence audit:
  *"cosine of the best-matching passage to the query."*
- **Whole-document full-text embedding** (alternative, not chosen). One embedding per document.
  Rejected for relevance because it is recall-inferior: averaging/truncating a long PDF dilutes the
  single smoking-gun passage that makes a document relevant.

**Choice:** max-chunk, as the recall-friendly default. The earlier "consistent with the
full-text dedup embedding" argument is a **category error**: dedup asks *is doc ≈ doc* (whole-doc is
right there), relevance asks *does a passage match the query* (max-chunk is right here) — two
operations, two granularities. Whole-doc is recorded as the rejected alternative; it is **not**
silently blended in (no mixed score).

### D16 — Dedup as relations; representative chosen AFTER ranking, query-independent tiebreak
Near-duplicate detection uses the whole-document full-text embeddings (doc≈doc granularity, D15)
plus the existing MinHash candidate generation. Duplicates are **not dropped silently**: each is
linked by a `duplicate-of` relation (the spelregels "relaties tussen documenten"). Two gaps from the
first draft are closed:
- **(a) Order is rank-then-representative.** "Highest relevance" makes the representative
  query-dependent, so the duplicate-collapse cannot run *before* ranking. The relevance ranking is
  computed over the **full candidate set including duplicates**; only then, within each duplicate
  group, the **highest-ranked** member is the representative that occupies a slot and the rest are
  collapsed with a logged reason. This order is explicit and is what keeps the "cosine ranks the
  full set" invariant (D20.5) intact.
- **(b) Tiebreak is query-independent and stable.** The content-addressed id cannot break ties
  between *exact* duplicates (they share the same hash). Ties on relevance are therefore broken by a
  query-independent stable key — ingestion order (or the source path) — so the representative is
  deterministic and reproducible.

### D17 — Out-of-scope is a process-role axis, separate from theme
"Buiten reikwijdte" is a classification of a document's **process role**, not its subject:
doorstuurmail (forward-only), agendaverzoek (calendar invite), procesmelding (process
notification), eerdere mail al vertegenwoordigd door de thread-head, dubbeling. A document matching
a role is marked `out_of_scope` with a logged reason (rules-first; the existing `scope-filter`
already enumerates these roles). This axis is **orthogonal** to theme: it is never a theme cluster,
and the theme remainder bucket **"Overig" is never equated with "buiten reikwijdte"**. A document
can be on-theme and out-of-scope (a forwarded copy of a relevant memo) or off-theme and in-scope.

### D18 — The report is navigation/transparency on the fixed top-100
The deliverable report (the existing self-contained `viewer-ui` `report.html`) renders the
**already-fixed** top-100. It clusters those 100 at chunk-level into onderwerp/deelonderwerp (reuse
of the `topic-clustering` machinery) purely as a **choice-menu** for the requester. The report:
- carries the **refined query in its meta** (this artifact is explicitly *about a query* — the
  thing that distinguishes it from the discover-report);
- shows per document its **relevance score** and a **"why"** — the contributing passage/terms (the
  highest-similarity chunk and/or the query terms it overlaps; the LLM rationale when available);
- shows the excluded rest grouped by reason (validity vs process-role out-of-scope).
Clustering here is cosmetic navigation and **never** changes which 100 documents are shown.

### D19 — Cluster the 100 vs tag the 100 in the corpus-landkaart (RECORD BOTH)
Two ways to give the requester a navigable view of the selection:
- **Cluster the top-100 on their own** (chosen default). Run the clustering over exactly the 100
  selected documents. Pros: the deliverable is self-contained and about the selection; labels
  describe the selected core; no dependency on a separate full-corpus run. Cons: the 100 may
  cluster differently than they would inside the full corpus.
- **Tag the 100 inside the discover corpus-landkaart.** Reuse the full-corpus clustering and
  highlight which documents are selected. Pros: situates the selection in the whole picture. Cons:
  couples the deliverable to a discover run, and the landkaart is dominated by the ~900
  non-selected documents.

**Choice:** cluster the top-100 on their own — the boring default that keeps the deliverable
self-contained and about the query. Tagging-in-the-landkaart is recorded as a future cross-reference,
not the deliverable. **Caveat:** the menu-clustering parameters SHALL be scaled to ~100 documents
and SHALL NOT reuse the discover defaults — `min_cluster_size=5` calibrated on a 403-document corpus
behaves differently on 100 (it would pool too much into a large "Overig"). The converge menu-cluster
params are an independent, ~100-scaled config, recorded separately from the discover defaults.

### D20 — Hard invariants (the contract this change locks)
1. The top-100 is fixed by the relevance ranking **before** any UI interaction — one documented,
   reproducible selection, independent of what a user clicks.
2. A cluster label **never** filters the ranking: a document that would cluster into "Overig" but
   ranks in the top-100 stays in the top-100.
3. Process-role (out-of-scope) and theme (cluster) are **two separate axes**; neither is derived
   from or equated with the other.
4. The relevance score is **never** mixed with cluster membership — no `w·nabijheid + (1−w)·
   lidmaatschap`, no magic weights. Relevance is the cosine, full stop.
5. **No hidden recall-gate before the selector.** The cosine ranks the **full candidate set**, not
   the rerank/score survivors. No stage demotes or excludes a candidate before the cosine ranking;
   the rerank score and the LLM relevance score are side-scores (transparency/"why"), never a filter
   on which documents can be selected.

### D21 — Transparency log (spelregels)
The audit-trail records, for every run: which query/queries were used; how relevance was determined
(the cosine rule + the embedding model id); which embedding model ran and where (sovereign/Ollama
profile, location=local); and, when an LLM produced labels/rationale, the exact prompt, model and
location per call. This is what lets a reviewer reconstruct and contest the selection after the fact.

### D22 — Final-score flow: rewire to close the hidden recall-gate
Verified in the current code (as of `ede388d`), three stages write `final` and one demotes — so the
cosine is *not* the selector today: `retrieve()` records `embed_sim` (max-chunk cosine) but **not**
`final`; `rerank()` sets `final = rerank`; `score()` sets `final = llm_relevance` for the scored
top-K and demotes the rest to `final = 0.0`. The net effect is a recall-gate: only the top-K rerank
survivors can be selected, and BM25/rerank silently excludes documents before the cosine matters —
exactly the "miss relevant documents" failure mode.

The rewire (blast radius across **three** code sites, larger than "MODIFIED retrieve-rerank"):
- **`retrieve.py`** sets `final = relevance` (the max-chunk cosine, D15) on **every** candidate.
- **`rerank.py`** no longer writes `final`; `rerank` stays a side-score for inspection only.
- **`score.py`** no longer writes `final` and **no longer demotes** to `0.0`; `llm_relevance` and the
  rationale are side outputs (the "why", D14/D23).
Under `--no-llm`, `final` is the cosine as well (today it stays the BM25 rerank score — that must
change too). One sentence holds in every mode: *the selection cut is taken on the cosine of the
best-matching passage to the query, over the full candidate set.*

### D23 — The "why" anchor is deterministic; the LLM rationale is a labelled, non-load-bearing gloss
The load-bearing "why" for each selected document is **deterministic and reproducible**: the
best-matching passage (the chunk that produced the max cosine) plus the query terms it overlaps.
The LLM rationale (change #2's output) MAY be shown only as a clearly-labelled, non-load-bearing
gloss; on any conflict the deterministic anchor wins. For now the report leans purely on the
deterministic anchor; the LLM gloss is marked a later nice-to-have. Coherence note: **change #2 is
reframed** — its *score* (`llm_relevance`) no longer selects, and its *rationale* becomes the
optional "why" gloss. Do not optimise the number that no longer selects.
