## MODIFIED Requirements

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
