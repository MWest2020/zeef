## ADDED Requirements

### Requirement: Exclude mechanically-unusable documents before scoring
The system SHALL, after ingest and before the retrieve/score stages, run a deterministic validity
gate that excludes documents which cannot be assessed: documents that failed to parse and documents
whose extractable text falls below a configured minimum. An excluded document SHALL be marked
`out_of_scope` with a machine-distinguishable validity reason (for example `validity:corrupt-pdf`,
`validity:empty-after-ocr`). The gate SHALL make no LLM call and SHALL be fully deterministic.

#### Scenario: An unparseable PDF is excluded with a reason
- **WHEN** the validity gate runs over a document whose ingest recorded `parse_ok = false`
- **THEN** the document is marked `out_of_scope` with reason `validity:corrupt-pdf`
- **AND** an audit event records the document id, the check that fired and the reason

#### Scenario: An empty-after-OCR document is excluded
- **WHEN** a document's recorded `char_count` is below the configured minimum and no redaction
  signal is present
- **THEN** the document is marked `out_of_scope` with reason `validity:empty-after-ocr`
- **AND** the document does not reach the retrieve/score stages

### Requirement: Preserve redacted-but-readable documents
The system SHALL NOT exclude a low-text document as empty when redaction signal is present. When a
document's extractable text is below the minimum but its recorded `redaction_ratio` meets or exceeds
the configured threshold, the document SHALL remain eligible for scoring (`undecided`) and SHALL be
flagged in its `decision_reason` as reduced-readability / probably redacted.

#### Scenario: A heavily redacted document is kept, not excluded
- **WHEN** a document is below the minimum text threshold but its `redaction_ratio` meets the
  configured threshold
- **THEN** the document remains `undecided` and is flagged as probably redacted
- **AND** it is still eligible for the retrieve/score stages

### Requirement: Validity exclusion is distinct from relevance
The validity gate SHALL only remove documents that cannot be assessed; it SHALL NOT change the
relevance threshold or the recall behaviour of the selection. Validity exclusions SHALL be
reportable as a category separate from semantic out-of-scope.

#### Scenario: Run summary separates validity exclusions from semantic exclusions
- **WHEN** a convergence run completes
- **THEN** the run summary reports the count of documents excluded by the validity gate separately
  from documents excluded by the semantic scope-filter

#### Scenario: Validity gate does not alter relevance recall
- **WHEN** the validity gate runs on a set containing only usable documents
- **THEN** no document is excluded by the gate
- **AND** the set reaching the retrieve/score stages is unchanged
