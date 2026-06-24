## ADDED Requirements

### Requirement: Ingest records extraction-health metadata
The ingest stage SHALL, for each loaded `Document`, record deterministic extraction-health metadata
that the validity gate consumes without re-reading the source file: the extracted character count
(`char_count`), whether parsing succeeded (`parse_ok`), and a redaction signal ratio
(`redaction_ratio`). These values SHALL be present on every ingested document.

#### Scenario: A successfully parsed PDF carries health metadata
- **WHEN** a PDF is ingested and its text is extracted
- **THEN** the resulting document records `char_count`, `parse_ok = true` and a `redaction_ratio`

#### Scenario: A PDF that fails to parse is recorded, not dropped
- **WHEN** a PDF cannot be parsed during ingest
- **THEN** a document is still produced with `parse_ok = false` recorded
- **AND** the failure is left for the validity gate to act on, not silently discarded at ingest
