## Why

One of the headline criteria for the BZK/ECP exploration is splitting the selection into
sub-topics: *"divide the documents into sub-topics or categories, to present as a choice menu to
the requester."* The pipeline does not produce this, and it is the largest open gap under the
criteria measured on the day. On top of that, the `category` column in `inventory.xlsx` currently
carries the `doc_type` (`email`, `pdf_digital`, …) — a column named "category" that actually holds
a file type reads as a thematic category. That is misleading, and there is no artifact a requester
can walk through as a menu over the core.

This is exactly where an LLM earns its place: judgement under linguistic ambiguity, where a label
raises defensibility — naming a coherent group of documents. The *grouping* itself has a
mechanical basis (similarity) and stays deterministic. So the change keeps the rule for the format
(design D9 of `criteria-scoring`): the LLM only labels; it never decides which documents belong
together.

## What Changes

A new stage runs after `select`, over the selected core (~100), and produces a two-level
**onderwerp → deelonderwerp** structure plus the artifact that becomes the requester's menu.

- **NEW** Topic clustering: deterministic hierarchical clustering over the already-computed
  document embeddings, cut at two heights → coarse (onderwerp) and fine (deelonderwerp). It is
  reproducible; the clustering parameters are recorded in the run-manifest.
- **NEW** Topic labelling: one LLM call per cluster turns representative snippets into a short
  Dutch label, logged with the exact prompt, model and location. Under `--no-llm` the label
  degrades to deterministic most-distinctive-term labels, marked as a fallback.
- **NEW** `topics.json`: `onderwerp → deelonderwerp → [doc_ids]` with labels — the choice menu /
  "verwijzing naar lijstjes".
- **MODIFIED** `Document`: gains `topic` and `subtopic` (exactly one of each per document; see
  design T4).
- **MODIFIED** Export: the inventory `category` is rebound to the document's
  onderwerp/deelonderwerp; `doc_type` is preserved in its own column; `topics.json` is written.
- **MODIFIED** CLI: the summary reports the number of onderwerpen and deelonderwerpen.

## Capabilities

### New Capabilities
- `topic-clustering`: group the core into a two-level onderwerp/deelonderwerp structure via
  deterministic clustering, label it with the LLM (deterministic fallback under `--no-llm`), and
  export a navigable `topics.json` menu.

### Modified Capabilities
- `export`: the inventory `category` reflects onderwerp/deelonderwerp (not the file type), with
  `doc_type` preserved in its own column.

## Impact

- **Affected specs**: new `topic-clustering`; modified `export`.
- **Affected code**: new `pipeline/topics.py`; `models.py` (`Document.topic`, `Document.subtopic`);
  `export.py` (`write_topics`, `category` rebind, `INVENTORY_COLUMNS`); `pipeline/run.py` (stage
  after `select`, before `export`); `config.py` (distance thresholds, min cluster size); `cli.py`.
- **New dependency**: `scipy` (hierarchical clustering over embeddings) under the `sovereign`
  extra — standard, well-understood, deterministic. The import path stays light: it is imported
  only inside the stage.
- **Determinism / sovereignty preserved**: the grouping is deterministic and reproducible; the LLM
  touches labels only (temperature-0 where the provider allows, prompt logged). Under `--no-llm`
  the labels fall back to distinctive terms and the stage stays air-gapped.
- **Out of scope (follow-up)**: per-document ≤100-word summary and `overlaps-with` cleanup
  (`output-hygiene`); the viewer that renders `topics.json` (`viewer-ui`); multiple assignment —
  v1 assigns exactly one onderwerp/deelonderwerp per document (design T4).
