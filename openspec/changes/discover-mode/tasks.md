## 1. Orkestratie (run_discover)

- [ ] 1.1 `run.py`: een `run_discover(docs_dir, providers, out_dir, audit, *, params...)` naast `run_converge`
- [ ] 1.2 Stage-volgorde: `ingest` → `validity` → `relate` (dedup) → embed-chunks → `cluster_topics`; query-gedreven stages (criteria/retrieve/rerank/score/select) overslaan
- [ ] 1.3 Chunks embedden vóór de clustering (expliciete embed-stap of de bestaande `_chunk_vectors`-fallback — kies de goedkoopste, resultaat moet identiek/deterministisch zijn)
- [ ] 1.4 `cluster_topics` voeden met het volledige valide, gededupliceerde corpus i.p.v. `selected`
- [ ] 1.5 Per-stage wall-clock loggen, zoals in `run_converge`

## 2. Per-cluster samenvatting

- [ ] 2.1 Een dunne samenvattingsvariant die op cluster-representanten (medoid-eerst) draait i.p.v. per document
- [ ] 2.2 LLM raakt alleen labels + per-cluster samenvatting; onder `--no-llm` geen samenvatting (TF-IDF-labels blijven)
- [ ] 2.3 Prompt, model en locatie per call in de audit-log (zelfde discipline als `summarise`/`topic_labels`)

## 3. Parameters & defaults

- [ ] 3.1 `min_cluster_size`, `onderwerp_distance`, `deelonderwerp_distance`, `max_chunks_per_doc` als discover-opties met passende defaults (niet de converge-defaults die op kleine selecties mikken)
- [ ] 3.2 Gekozen parameters + embedding-bron in het run-manifest

## 4. CLI + uitvoer

- [ ] 4.1 `cli.py`: `discover`-commando (Typer), `--out`, profiel-/`--no-llm`-vlaggen, clustering-opties
- [ ] 4.2 Runmap-uitvoer: landkaart als JSON (onderwerpen → deelonderwerpen → doc_ids + labels + samenvattingen), `audit.jsonl`, `report/`-viewer
- [ ] 4.3 Beknopte terminal-samenvatting (onderwerpen/deelonderwerpen/documenten)

## 5. Tests

- [ ] 5.1 Discover op een fixture-corpus: levert geneste onderwerpen, geen query-gedreven selectie uitgevoerd
- [ ] 5.2 Determinisme: tweemaal draaien geeft identieke landkaart
- [ ] 5.3 `--no-llm`: TF-IDF-labels, geen samenvattingen, geen model-call
- [ ] 5.4 Per-cluster samenvatting wordt op representanten gemaakt, niet per document (call-telling)
- [ ] 5.5 Manifest bevat clustering-parameters en embedding-bron
- [ ] 5.6 Begrensde looptijd op een corpus van honderden documenten (cap via `max_chunks_per_doc` werkt)
