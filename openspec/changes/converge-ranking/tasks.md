## 1. Relevance-ranking (the selector) + final-flow rewire

- [ ] 1.1 Relevance = max cosine of the document's chunk embeddings to the query (best-matching
      passage); recorded in `Document.scores` (e.g. `relevance`/`embed_sim`); deterministic for a
      given corpus + query + chunk size + model
- [ ] 1.2 `retrieve.py` sets `final = relevance` on **every** candidate (incl. under `--no-llm`)
- [ ] 1.3 `rerank.py` stops writing `final`; keep `rerank` as a side-score only
- [ ] 1.4 `score.py` stops writing `final` and **stops demoting to `0.0`**; keep `llm_relevance` +
      rationale as side outputs (no recall-gate)
- [ ] 1.5 Sort by `final` over the full candidate set; the ranking is the sole selector (no
      clustering, no score-mixing, no pre-demotion)
- [ ] 1.6 Log the relevance rule + embedding model id, and rerank/LLM scores as side-scores (D21)

## 2. Select (top-N, fixed before UI)

- [ ] 2.1 Cut the top-N by relevance ranking; `decision = selected` + reason naming the rule + N
- [ ] 2.2 The selection is fixed and serialized before any report/UI is produced; reproducible
- [ ] 2.3 Recall-bias applies only at the cutoff (ties/near-threshold), logged; never via clusters
- [ ] 2.4 A document that would cluster into "Overig" but ranks in the top-N is still selected

## 3. Relate (dedup as relations, representative)

- [ ] 3.1 Near-duplicate detection on the whole-document full-text embeddings + MinHash candidates
- [ ] 3.2 Collapse duplicates **after** ranking: the highest-**ranked** member is the representative;
      ties broken by a query-independent stable key (ingestion order / source path), not content-id
- [ ] 3.3 Log every non-representative duplicate with a reason; keep it as a `duplicate-of` relation
      (visible, not silently dropped)

## 4. Scope-filter (process-role axis)

- [ ] 4.1 Classify process role rules-first: doorstuurmail, agendaverzoek, procesmelding, eerdere
      mail al vertegenwoordigd door de thread-head, dubbeling → `out_of_scope` + logged reason
- [ ] 4.2 Keep this axis orthogonal to theme: never emit a theme cluster here, never equate "Overig"
      (theme) with "buiten reikwijdte" (role)

## 5. Report (navigation on the fixed top-100)

- [ ] 5.1 Cluster exactly the selected top-N (chunk-level) into onderwerp/deelonderwerp as a menu
      (reuse `topic-clustering`) with menu-cluster params scaled to ~100, **independent of the
      discover defaults**; clustering never changes which documents are shown
- [ ] 5.2 Put the refined query in the report meta (distinguishes it from the discover-report)
- [ ] 5.3 Per document: relevance score + a **deterministic** "why" (best-matching passage +
      overlapping query terms); any LLM rationale shown only as a labelled, non-load-bearing gloss
- [ ] 5.4 Show the excluded rest grouped by reason, validity vs process-role out-of-scope

## 6. Transparency log

- [ ] 6.1 Record query/queries, the relevance method (cosine + model id), embedding model +
      location, and the exact LLM prompts (when labels/rationale are produced)

## 7. Tests

- [ ] 7.1 Ranking is deterministic: same corpus + query + model → identical top-N
- [ ] 7.2 Selection is fixed before UI: the serialized top-N does not depend on any report step
- [ ] 7.3 Invariant: a document in the "Overig" cluster but high-ranking is in the top-N
- [ ] 7.4 No score-mixing: relevance equals the cosine, independent of cluster membership
- [ ] 7.5 Dedup: a duplicate group yields one ranked representative (after ranking, query-independent
      tiebreak) + logged relations for the rest
- [ ] 7.6 Axes separate: an on-theme but out-of-scope document is excluded by role, not by theme
- [ ] 7.7 Report meta carries the query; per-document deterministic "why" is present
- [ ] 7.8 No recall-gate: `final` is the passage cosine on every candidate; no rerank/score stage
      writes `final` or demotes a candidate to `0.0`
- [ ] 7.9 Max-chunk: a document relevant only in one passage ranks on that passage, not a diluted
      whole-document average
