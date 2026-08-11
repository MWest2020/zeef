## ADDED Requirements

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
