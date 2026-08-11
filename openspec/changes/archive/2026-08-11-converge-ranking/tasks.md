## 1. Relevance-ranking (the selector) + final-flow rewire

- [x] 1.1 Relevance = max cosine of the document's chunk embeddings to the query (best-matching
      passage); recorded in `Document.scores` (e.g. `relevance`/`embed_sim`); deterministic for a
      given corpus + query + chunk size + model → `retrieve.py` (`embed_sim`)
- [x] 1.2 `retrieve.py` sets `final = relevance` on **every** candidate (incl. under `--no-llm`)
- [x] 1.3 `rerank.py` stops writing `final`; keep `rerank` as a side-score only
- [x] 1.4 `score.py` stops writing `final` and **stops demoting to `0.0`**; keep `llm_relevance` +
      rationale as side outputs (no recall-gate)
- [x] 1.5 Sort by `final` over the full candidate set; the ranking is the sole selector (no
      clustering, no score-mixing, no pre-demotion) → `select._ordered`
- [x] 1.6 Log the relevance rule + embedding model id, and rerank/LLM scores as side-scores (D21)
      → `retrieve` first-pass event (`method=max-cosine-best-passage`, model+location)

## 2. Select (top-N, fixed before UI)

- [x] 2.1 Cut the top-N by relevance ranking; `decision = selected` + reason naming the rule + N
- [x] 2.2 The selection is fixed and serialized before any report/UI is produced; reproducible
      → `run.py`: select runs before topics/summarise/export
- [x] 2.3 Recall-bias applies only at the cutoff (ties/near-threshold), logged; never via clusters
- [x] 2.4 A document that would cluster into "Overig" but ranks in the top-N is still selected
      → select ignores `topic` (clustering runs after select); test_cluster_membership...

## 3. Relate (dedup as relations, representative)

- [x] 3.1 Near-duplicate detection on the whole-document full-text embeddings + MinHash candidates
      → `relate`/`dedup.py` (unchanged: detect + relate only)
- [x] 3.2 Collapse duplicates **after** ranking: the highest-**ranked** member is the representative;
      ties broken by a query-independent stable key (ingestion order / source path), not content-id
      → `select._collapse_duplicates` (rank → group by `duplicate-of` → highest `final`, tiebreak source_path)
- [x] 3.3 Log every non-representative duplicate with a reason; keep it as a `duplicate-of` relation
      (visible, not silently dropped) → select emits `excluded` event; relation preserved

## 4. Scope-filter (process-role axis)

- [x] 4.1 Classify process role rules-first: doorstuurmail, agendaverzoek, procesmelding, eerdere
      mail al vertegenwoordigd door de thread-head, dubbeling → `out_of_scope` + logged reason.
      → `scope_rules.RULES` (forwarded-only/calendar-invite/process-notification/thread-tail).
      **Afwijking:** content-`dubbeling` is GEEN scope-rule meer — dat zou een recall-gate vóór de
      ranking zijn (D20.5); die collapse verhuisde naar `select` (3.2). De thread-tail-rol dekt
      "eerdere mail al vertegenwoordigd door de thread-head".
- [x] 4.2 Keep this axis orthogonal to theme: never emit a theme cluster here, never equate "Overig"
      (theme) with "buiten reikwijdte" (role) → scope-filter zet alleen `decision`, geen cluster

## 5. Report (navigation on the fixed top-100)

- [x] 5.1 Cluster exactly the selected top-N (chunk-level) into onderwerp/deelonderwerp as a menu
      (reuse `topic-clustering`) with menu-cluster params scaled to ~100, **independent of the
      discover defaults** → `run.py` clusters `selected`; converge-defaults (mcs=3, 0.8/0.5) zijn
      aparte constanten, los van de discover-defaults (mcs=5, 0.50/0.42)
- [x] 5.2 Put the refined query in the report meta (distinguishes it from the discover-report)
      → `build_report_data(query=...)`
- [x] 5.3 Per document: relevance score + a **deterministic** "why" (best-matching passage +
      overlapping query terms); any LLM rationale shown only as a labelled, non-load-bearing gloss
      → `best_passage` + `term_overlap`; report.html labelt de LLM-motivatie als "indicatief"
- [x] 5.4 Show the excluded rest grouped by reason, validity vs process-role out-of-scope
      → `write_excluded` + report.html (validity/semantic, per reden)

## 6. Transparency log

- [x] 6.1 Record query/queries, the relevance method (cosine + model id), embedding model +
      location, and the exact LLM prompts (when labels/rationale are produced)
      → retrieve first-pass (method+model+location), score llm-score (prompt+model+location)

## 7. Tests

- [x] 7.1 Ranking is deterministic: same corpus + query + model → identical top-N
      → test_ranking_is_deterministic
- [x] 7.2 Selection is fixed before UI: the serialized top-N does not depend on any report step
      → test_e2e (select before export); run.py ordering
- [x] 7.3 Invariant: a document in the "Overig" cluster but high-ranking is in the top-N
      → test_cluster_membership_does_not_filter_selection
- [x] 7.4 No score-mixing: relevance equals the cosine, independent of cluster membership
      → test_final_is_passage_cosine_and_no_stage_demotes + test_cluster_membership...
- [x] 7.5 Dedup: a duplicate group yields one ranked representative (after ranking, query-independent
      tiebreak) + logged relations for the rest → test_duplicate_group_collapses... +
      test_exact_duplicate_tiebreak_is_query_independent
- [x] 7.6 Axes separate: an on-theme but out-of-scope document is excluded by role, not by theme
      → test_scope_filter (process-role rules, orthogonal to theme)
- [x] 7.7 Report meta carries the query; per-document deterministic "why" is present
      → test_report_carries_query_and_deterministic_why
- [x] 7.8 No recall-gate: `final` is the passage cosine on every candidate; no rerank/score stage
      writes `final` or demotes a candidate to `0.0` → test_final_is_passage_cosine_and_no_stage_demotes
- [x] 7.9 Max-chunk: a document relevant only in one passage ranks on that passage, not a diluted
      whole-document average → test_relevance_uses_best_matching_passage_not_average
