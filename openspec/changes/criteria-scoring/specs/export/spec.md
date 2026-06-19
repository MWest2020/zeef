## MODIFIED Requirements

### Requirement: Inventory export
The system SHALL write an `inventory.xlsx` for the selected core with one row per selected
document and the columns `id`, `score`, `category`, `summary`, `reason`, and `motivatie`. The
`motivatie` column SHALL carry the per-document relevance rationale (empty when no LLM scoring
ran, e.g. under `--no-llm`). The `reason` column SHALL keep recording the selection arithmetic
(mode, parameter, final score versus cutoff).

#### Scenario: Inventory has the required columns including motivatie
- **WHEN** the inventory is written for a selection
- **THEN** the header is exactly `id, score, category, summary, reason, motivatie`
- **AND** each selected document contributes one row

#### Scenario: Rationale is empty without LLM scoring
- **WHEN** a run uses `--no-llm`
- **THEN** the `motivatie` column is empty for every row

## ADDED Requirements

### Requirement: Criteria artifact export
The system SHALL write a `criteria.json` artifact to the run output directory recording the
articulated relevance criteria and the query they were derived from, so the relevance definition
used for the run is reviewable alongside the inventory.

#### Scenario: criteria.json accompanies the run outputs
- **WHEN** a convergence run completes
- **THEN** the run output directory contains `criteria.json` next to `inventory.xlsx`,
  `relations.json` and `audit.jsonl`
