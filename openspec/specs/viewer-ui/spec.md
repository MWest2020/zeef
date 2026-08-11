# viewer-ui Specification

## Purpose
TBD - created by archiving change viewer-ui. Update Purpose after archive.
## Requirements
### Requirement: Produce a self-contained offline HTML report
The system SHALL produce a single self-contained `report.html` file that opens without a server or
network access, with the run data embedded inline in a `<script type="application/json">` block.
The report SHALL load no external resources: no CDN, no remote fonts, no remote scripts, and SHALL
issue no network requests (no `fetch`/`XMLHttpRequest`, no external `<script src>` or `<link>`).

#### Scenario: The report opens offline with no external requests
- **WHEN** `report.html` is opened from the local filesystem with no network available
- **THEN** the report renders fully from the inline data
- **AND** it references no external URL and issues no network request

### Requirement: Present the selected core as a navigable topic menu
The report SHALL present the selected core grouped by onderwerp and deelonderwerp as a collapsible
menu, and SHALL show, per document, its relevance score, rationale, summary (when present),
selection reason, redaction status, and its relations.

#### Scenario: A reviewer navigates the selection by topic
- **WHEN** a reviewer opens the report for a completed run
- **THEN** the selected documents are grouped under their onderwerp/deelonderwerp
- **AND** opening a document shows its score, rationale, summary (when present), reason and relations

#### Scenario: A redacted-but-kept document shows its redaction status
- **WHEN** a document carries the canonical redaction marking in its metadata
- **THEN** the report shows it as reduced-readability / probably redacted
- **AND** this status is read from the canonical metadata key, not from `decision_reason`

### Requirement: Show both the selected core and the excluded rest
The report SHALL show the excluded documents grouped by exclusion reason, distinguishing validity
exclusions (`validity:*`) from semantic out-of-scope, so that both the selected 100 and the rest are
inspectable.

#### Scenario: The excluded rest is inspectable with reasons
- **WHEN** a reviewer opens the report
- **THEN** the excluded documents are shown grouped by their exclusion reason
- **AND** validity exclusions are distinguishable from semantic out-of-scope exclusions

### Requirement: Escape untrusted text in the report
The system SHALL escape all untrusted text — LLM summaries and topic labels, document titles — when
rendering the report, so that content originating from a document cannot execute as markup. The
inline JSON SHALL be escaped so document content cannot terminate the `<script>` block.

#### Scenario: A markup payload is shown as text, not executed
- **WHEN** a document's summary, label or title contains an HTML/script payload
- **THEN** the generated report contains the payload only in an escaped form
- **AND** the payload does not appear as a live `<script>` tag that would execute

