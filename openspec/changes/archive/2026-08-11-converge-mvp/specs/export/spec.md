## ADDED Requirements

### Requirement: Excel inventory of the selection
The system SHALL export an `inventory.xlsx` listing, per selected document, at least its id,
final score, category, summary, and decision reason. When summaries are unavailable (e.g.
`--no-llm`), the summary column SHALL be left empty rather than omitted.

#### Scenario: Inventory columns present
- **WHEN** a converge run completes
- **THEN** `inventory.xlsx` contains a row per selected document with id, score, category,
  summary, and reason columns

#### Scenario: No-LLM run leaves summary empty
- **WHEN** the run used `--no-llm`
- **THEN** the inventory still lists each selected document with an empty summary column

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
