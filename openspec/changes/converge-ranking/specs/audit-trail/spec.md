## ADDED Requirements

### Requirement: Transparency log for the converge selection
The system SHALL record, for every converge run, the information needed to reconstruct and contest
the selection after the fact (the spelregels transparency requirement): the refined query (and any
additional queries used); how relevance was determined (the cosine-of-whole-document rule and the
embedding model id); which embedding model ran and where (the profile and `location`, e.g.
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
