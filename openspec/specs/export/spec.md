# export Specification

## Purpose
TBD - created by archiving change converge-mvp. Update Purpose after archive.
## Requirements
### Requirement: Excel inventory of the selection
The system SHALL export an `inventory.xlsx` listing, per selected document, at least its id,
final score, category, summary, decision reason, a `motivatie` column, and a `doc_type` column.
The `category` column SHALL carry the document's onderwerp/deelonderwerp (its position in the topic
structure), not its file type; the file type SHALL be preserved in its own `doc_type` column so no
information is lost. The `motivatie` column SHALL carry the per-document relevance rationale (empty
when no LLM scoring ran, e.g. under `--no-llm`). The `reason` column SHALL keep recording the
selection arithmetic (mode, parameter, final score versus cutoff). When summaries are unavailable
(e.g. `--no-llm`), the summary column SHALL be left empty rather than omitted.

#### Scenario: Inventory columns present
- **WHEN** a converge run completes
- **THEN** `inventory.xlsx` contains a row per selected document with id, score, category,
  summary, reason, motivatie, and doc_type columns

#### Scenario: Category is the topic, not the file type
- **WHEN** the inventory is exported for a run with topic-clustering
- **THEN** the `category` column contains the document's onderwerp/deelonderwerp
- **AND** the document's file type is available in a separate `doc_type` column

#### Scenario: No-LLM run leaves summary and rationale empty
- **WHEN** the run used `--no-llm`
- **THEN** the inventory still lists each selected document with an empty summary column
- **AND** the `motivatie` column is empty for every row

#### Scenario: Selection arithmetic is unaffected
- **WHEN** the inventory is exported
- **THEN** the `reason` column still records the selection arithmetic (mode, parameter, final
  score versus cutoff)

### Requirement: Relations graph export
The system SHALL export a `relations.json` capturing the relation graph (thread, attachment,
duplicate, overlap edges) between documents.

#### Scenario: Relations exported as a graph
- **WHEN** a converge run completes
- **THEN** `relations.json` contains the typed edges between document ids

### Requirement: Audit-log delivered with outputs
The system SHALL write the run's `audit.jsonl` to the run output directory alongside the
inventory and relations graph.

#### Scenario: Audit-log present in outputs
- **WHEN** a converge run completes
- **THEN** the output directory contains `audit.jsonl`, `inventory.xlsx`, and `relations.json`

### Requirement: The summary column is populated or omitted, never empty
The export stage SHALL include the `summary` column in `inventory.xlsx` only when summaries were
produced (an LLM was available); under `--no-llm` it SHALL omit the column entirely rather than emit
an empty one. When present, each cell SHALL contain the document's content summary.

#### Scenario: Summary column present and populated with an LLM
- **WHEN** the inventory is exported for a run with an LLM available
- **THEN** the inventory contains a `summary` column populated with each document's summary

#### Scenario: No-LLM run omits the summary column
- **WHEN** the inventory is exported under `--no-llm`
- **THEN** the inventory does not contain a `summary` column

### Requirement: Export the full excluded set and generate the report
The export stage SHALL write the full set of excluded documents with their exclusion reasons in a
machine-readable form (`excluded.json`), distinguishing validity exclusions from semantic
out-of-scope, and SHALL generate `report.html` with the run data (selected core with topics,
summaries, rationales, redaction status and relations; excluded set with reasons) embedded inline.

#### Scenario: The excluded set and report are written for a run
- **WHEN** a convergence run completes
- **THEN** a machine-readable `excluded.json` is present in the run output directory
- **AND** a `report.html` embedding the run data is present in the run output directory

#### Scenario: Excluded entries carry their reason category
- **WHEN** `excluded.json` is written
- **THEN** each entry records its reason and whether it is a validity exclusion or semantic
  out-of-scope

### Requirement: Criteria artifact export
The system SHALL write a `criteria.json` artifact to the run output directory recording the
articulated relevance criteria and the query they were derived from, so the relevance definition
used for the run is reviewable alongside the inventory.

#### Scenario: criteria.json accompanies the run outputs
- **WHEN** a convergence run completes
- **THEN** the run output directory contains `criteria.json` next to `inventory.xlsx`,
  `relations.json` and `audit.jsonl`

