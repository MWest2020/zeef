# audit-trail Specification

## Purpose
TBD - created by archiving change converge-mvp. Update Purpose after archive.
## Requirements
### Requirement: Append-only JSONL audit-trail
The system SHALL write one structured JSONL event per stage action to an append-only
`audit.jsonl`. Each event SHALL include a timestamp, the stage name, the affected document
id(s), the action taken, and the relevant inputs (e.g. query, thresholds, mode). Stages SHALL
use structured logging only and SHALL NOT emit ad-hoc prints in place of audit events.

#### Scenario: Each stage emits events
- **WHEN** the pipeline runs end to end
- **THEN** `audit.jsonl` contains events for ingest, relate, scope-filter, retrieve, rerank, and
  select

### Requirement: Model identity and execution location recorded
Every event produced by an LLM, embedding, or reranker call SHALL record the model id and where
it ran (`local` or `cloud`), and every LLM event SHALL record the exact prompt sent.

#### Scenario: LLM event carries prompt and location
- **WHEN** the scope-filter invokes the LLM on an edge-case document
- **THEN** the audit event records the model id, `location`, and the exact prompt text

### Requirement: Selection and exclusion fully reconstructable
The audit-trail SHALL allow both the selected core and the excluded rest to be reconstructed
from the log alone, including the reason for each document's decision.

#### Scenario: Reconstruct a decision from the log
- **WHEN** a reviewer inspects `audit.jsonl` after a run
- **THEN** they can determine, for any document, whether it was selected or excluded and why

### Requirement: Transparency log for the converge selection
The system SHALL record, for every converge run, the information needed to reconstruct and contest
the selection after the fact (the spelregels transparency requirement): the refined query (and any
additional queries used); how relevance was determined (the cosine-of-best-matching-passage rule and
the embedding model id); which embedding model ran and where (the profile and `location`, e.g.
sovereign/Ollama, `location=local`); and, when an LLM produced topic labels or a per-document
rationale, the exact prompt, model and location of each such call.

#### Scenario: The run records its query and relevance method
- **WHEN** a converge run completes
- **THEN** the audit-log contains the refined query and a record of the relevance method (the
  cosine rule and the embedding model id)

#### Scenario: The model and its location are recorded
- **WHEN** relevance is computed with the sovereign embedding model
- **THEN** the audit-log records the embedding model id and that it ran locally (sovereign profile)

#### Scenario: LLM label prompts are recorded
- **WHEN** an LLM produces topic labels or a per-document rationale
- **THEN** each such call is recorded with its exact prompt, model and location

#### Scenario: Side-scores are logged as transparency, not selection
- **WHEN** a rerank score or an LLM relevance score is produced
- **THEN** it is recorded in the audit-log as a side-score for transparency
- **AND** the log shows the selection cut was taken on the passage cosine, not on these side-scores

