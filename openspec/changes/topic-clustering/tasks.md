## 1. Data model

- [ ] 1.1 Add `Document.topic: str = ""` and `Document.subtopic: str = ""` to `models.py`
- [ ] 1.2 Keep them out of any deterministic id derivation (labels, not identity)

## 2. Config

- [ ] 2.1 `config.py`: add `onderwerp_distance`, `deelonderwerp_distance`, `min_cluster_size` (conservative defaults), in their own block (parallel-merge-safe with `pdf-validity-gate`)
- [ ] 2.2 Record the three clustering parameters in the run-manifest params

## 3. Clustering stage (deterministic)

- [ ] 3.1 `pipeline/topics.py`: `cluster_topics(selected, providers, audit) -> selected`
- [ ] 3.2 Agglomerative hierarchical clustering (cosine, average linkage) over the existing embeddings; cut at two heights; `scipy.cluster.hierarchy` imported inside the stage
- [ ] 3.3 Collapse clusters below `min_cluster_size` into a single deterministic "Overig" onderwerp; record the collapse in the audit-log
- [ ] 3.4 Assign exactly one `topic` and one `subtopic` per selected document

## 4. Labelling (LLM + fallback)

- [ ] 4.1 Per cluster: pick representative snippets (medoid + nearest members: title + first lines) → one LLM call → short Dutch label; temperature-0; log the exact prompt, model and location
- [ ] 4.2 `--no-llm`: build labels from most-distinctive terms (TF-IDF cluster vs rest), mark `source: fallback`, make no LLM call

## 5. Export

- [ ] 5.1 `export.py`: `write_topics(...)` → `topics.json` (onderwerp → deelonderwerp → doc ids, with labels)
- [ ] 5.2 `export.py`: rebind the inventory `category` to onderwerp/deelonderwerp; add a `doc_type` column; update `INVENTORY_COLUMNS`

## 6. Wiring

- [ ] 6.1 `run.py`: run the `topics` stage after `select` and before `export`, inside the per-stage timer; add `topics.json` to the export artifact list (append-style; merge `run.py` last)
- [ ] 6.2 `cli.py`: summary reports the number of onderwerpen and deelonderwerpen

## 7. Tests

- [ ] 7.1 `test_topics.py`: deterministic grouping on a fixed embedding fixture; two levels; "Overig" collapse on a singleton
- [ ] 7.2 `--no-llm` term fallback produces labels and makes no LLM call
- [ ] 7.3 `topics.json` shape; inventory `category` = topic and `doc_type` in its own column (assert on column name, not index)
- [ ] 7.4 `openspec validate topic-clustering --strict`
- [ ] 7.5 Full suite green (`uv run pytest`), `ruff` clean, ≤200-line file check

## 8. Docs & changelog

- [ ] 8.1 `docs/.../de-pijplijn.md`: add the topics stage and the onderwerp/deelonderwerp menu; note the `category` rebind
- [ ] 8.2 README + artifact list: `topics.json` as a run output
- [ ] 8.3 `CHANGELOG.md`: dated entry (what, why, files, test result)
