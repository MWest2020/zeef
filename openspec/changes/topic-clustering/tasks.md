## 1. Data model

- [x] 1.1 Add `Document.topic: str = ""` and `Document.subtopic: str = ""` to `models.py`
- [x] 1.2 Keep them out of any deterministic id derivation (labels, not identity)

## 2. Config

- [x] 2.1 `config.py`: add `onderwerp_distance`, `deelonderwerp_distance`, `min_cluster_size` (conservative defaults), in their own block (parallel-merge-safe with `pdf-validity-gate`)
- [x] 2.2 Record the three clustering parameters in the run-manifest params

## 3. Clustering stage (deterministic)

- [x] 3.1 `pipeline/topics.py`: `cluster_topics(selected, providers, audit) -> menu` (mutates docs in place)
- [x] 3.2 Agglomerative hierarchical clustering (cosine, average linkage) over the existing embeddings; cut at two heights; `scipy.cluster.hierarchy` imported inside the stage
- [x] 3.3 Collapse clusters below `min_cluster_size` into a single deterministic "Overig" onderwerp; record the collapse in the audit-log
- [x] 3.4 Assign exactly one `topic` and one `subtopic` per selected document

## 4. Labelling (LLM + fallback)

- [x] 4.1 Per cluster: representative snippets (medoid + nearest members, title + first lines) → one LLM call → short Dutch label; prompt/model/location logged (`topic_labels._llm_label`). Tested with a spy LLM (label lands, `source != fallback`, audit event per cluster). Demo-model quality pass is manual, not in tests.
- [x] 4.2 `--no-llm`: build labels from most-distinctive terms (TF-IDF cluster vs rest), mark `source: fallback`, make no LLM call

## 5. Export

- [x] 5.1 `export.py`: `write_topics(...)` → `topics.json` (onderwerp → deelonderwerp → doc ids, with labels)
- [x] 5.2 `export.py`: rebind the inventory `category` to onderwerp/deelonderwerp; add a `doc_type` column; update `INVENTORY_COLUMNS`

## 6. Wiring

- [x] 6.1 `run.py`: run the `topics` stage after `select` and before `export`, inside the per-stage timer; add `topics.json` to the export artifact list (append-style; merge `run.py` last)
- [x] 6.2 `cli.py`: summary reports the number of onderwerpen and deelonderwerpen

## 7. Tests

- [x] 7.1 `test_topics.py`: deterministic grouping on a fixed embedding fixture; two levels; "Overig" collapse on a singleton
- [x] 7.2 `--no-llm` term fallback produces labels and makes no LLM call (explicit no-call assertion)
- [x] 7.3 `topics.json` shape; inventory `category` = topic and `doc_type` in its own column (assert on column name, not index)
- [x] 7.4 `openspec validate topic-clustering --strict`
- [x] 7.5 Full suite green (`uv run pytest`), `ruff` clean, ≤200-line file check
- [x] 7.6 Chunk→document aggregation (T7): a document with chunks split over two clusters gets exactly one onderwerp/deelonderwerp by majority, deterministically (the asymmetric failure mode)
- [x] 7.7 LLM-label branch tested with a spy: label lands on the cluster, `source` is no longer fallback, audit event per cluster with prompt/model/location

## 8. Docs & changelog

- [x] 8.1 `docs/.../de-pijplijn.md`: add the topics stage and the onderwerp/deelonderwerp menu; note the `category` rebind + the canonical topic field (T7)
- [x] 8.2 README + artifact list: `topics.json` as a run output
- [x] 8.3 `CHANGELOG.md`: dated entry (what, why, files, test result)
