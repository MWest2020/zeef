## MODIFIED Requirements

### Requirement: Excel inventory of the selection
The system SHALL export an `inventory.xlsx` listing, per selected document, at least its id,
final score, category, summary, decision reason, and a `motivatie` column. The `motivatie`
column SHALL carry the per-document relevance rationale (empty when no LLM scoring ran, e.g.
under `--no-llm`). The `reason` column SHALL keep recording the selection arithmetic (mode,
parameter, final score versus cutoff). When summaries are unavailable (e.g. `--no-llm`), the
summary column SHALL be left empty rather than omitted.

#### Scenario: Inventory columns present
- **WHEN** a converge run completes
- **THEN** `inventory.xlsx` contains a row per selected document with id, score, category,
  summary, reason, and motivatie columns

#### Scenario: No-LLM run leaves summary and rationale empty
- **WHEN** the run used `--no-llm`
- **THEN** the inventory still lists each selected document with an empty summary column
- **AND** the `motivatie` column is empty for every row

## ADDED Requirements

### Requirement: Criteria artifact export
The system SHALL write a `criteria.json` artifact to the run output directory recording the
articulated relevance criteria and the query they were derived from, so the relevance definition
used for the run is reviewable alongside the inventory.

#### Scenario: criteria.json accompanies the run outputs
- **WHEN** a convergence run completes
- **THEN** the run output directory contains `criteria.json` next to `inventory.xlsx`,
  `relations.json` and `audit.jsonl`
