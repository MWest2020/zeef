## ADDED Requirements

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
