## ADDED Requirements

### Requirement: Summarise each selected document in at most 100 words
The system SHALL, for each document in the selected core, produce a content summary of at most a
configured maximum number of words (default 100) using an `LLMProvider`, recording the exact prompt,
model and location in the audit-log. The summary SHALL describe the document's content and SHALL be
distinct from the per-document relevance rationale. Summarisation SHALL run after the select and
topic-clustering stages and only over the selected core.

#### Scenario: Selected documents are summarised
- **WHEN** the summarise stage runs with an LLM available
- **THEN** each selected document has a content summary no longer than the configured maximum
- **AND** an audit event records the exact prompt, the model and its location

#### Scenario: The summary is distinct from the rationale
- **WHEN** a selected document has both a relevance rationale and a content summary
- **THEN** the summary describes the document's content, separate from the rationale that explains
  why it scored

### Requirement: No summary and no LLM call under --no-llm
The system SHALL NOT produce summaries under `--no-llm` and SHALL make no LLM call for
summarisation.

#### Scenario: No-LLM run makes no summarisation call
- **WHEN** a convergence run completes under `--no-llm`
- **THEN** no summaries are produced
- **AND** no LLM call is made for summarisation
