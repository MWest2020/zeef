## ADDED Requirements

### Requirement: Export the full excluded set and generate the report
The export stage SHALL write the full set of excluded documents with their exclusion reasons in a
machine-readable form (`excluded.json`), distinguishing validity exclusions from semantic
out-of-scope, and SHALL generate `report.html` with the run data (selected core with topics,
summaries, rationales, redaction status and relations; excluded set with reasons) embedded inline.

#### Scenario: The excluded set and report are written for a run
- **WHEN** a convergence run completes
- **THEN** a machine-readable `excluded.json` is present in the run output directory
- **AND** a `report.html` embedding the run data is present in the run output directory

#### Scenario: Excluded entries carry their reason category
- **WHEN** `excluded.json` is written
- **THEN** each entry records its reason and whether it is a validity exclusion or semantic
  out-of-scope
