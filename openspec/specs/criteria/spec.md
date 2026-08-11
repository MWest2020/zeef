# criteria Specification

## Purpose
TBD - created by archiving change criteria-scoring. Update Purpose after archive.
## Requirements
### Requirement: Articulate explicit relevance criteria from the refined query
The system SHALL, before scoring, derive an explicit set of named relevance criteria from the
refined query using an `LLMProvider`. Each criterion SHALL have a human-readable label and
description. The articulated criteria SHALL be recorded in the audit-log with the exact prompt,
model and location, and SHALL be available to the relevance-scoring stage.

#### Scenario: Query is turned into named criteria
- **WHEN** criteria articulation runs for a refined query with an LLM available
- **THEN** a set of criteria (each with a label and description) is produced
- **AND** an audit event records the exact prompt, the model and its location

### Requirement: Deterministic fallback under --no-llm
The system SHALL, when no LLM is available (`--no-llm`), produce a single deterministic
criterion equal to the raw refined query, marked as a fallback, so the pipeline still runs
air-gapped. No LLM call SHALL be made in that case.

#### Scenario: No-LLM run falls back to the raw query
- **WHEN** criteria articulation runs under `--no-llm`
- **THEN** exactly one criterion equal to the raw query is produced, marked as a fallback
- **AND** no LLM call is made

### Requirement: Criteria are exported as an inspectable artifact
The system SHALL write the articulated criteria to a `criteria.json` artifact in the run output
directory, so a reviewer can read and contest the relevance definition used for the selection.

#### Scenario: criteria.json is written for a run
- **WHEN** a convergence run completes
- **THEN** a `criteria.json` file is present in the run output directory containing the criteria
  and the query they were derived from

