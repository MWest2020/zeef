## MODIFIED Requirements

### Requirement: Inventory export
The system SHALL write an `inventory.xlsx` for the selected core with one row per selected
document. The `category` column SHALL carry the document's onderwerp/deelonderwerp (its position in
the topic structure), not its file type. The document's file type SHALL be preserved in its own
`doc_type` column so no information is lost. The `summary`, `reason` and `motivatie` columns SHALL
keep their existing meaning (`reason` records the selection arithmetic; `motivatie` carries the
per-document relevance rationale, empty under `--no-llm`).

#### Scenario: Inventory shows the topic, not the file type, as category
- **WHEN** the inventory is exported for a run with topic-clustering
- **THEN** the `category` column contains the document's onderwerp/deelonderwerp
- **AND** the document's file type is available in a separate `doc_type` column

#### Scenario: Selection arithmetic and rationale are unaffected
- **WHEN** the inventory is exported
- **THEN** the `reason` column still records the selection arithmetic (mode, parameter, final score
  versus cutoff)
- **AND** the `motivatie` column still carries the per-document relevance rationale
