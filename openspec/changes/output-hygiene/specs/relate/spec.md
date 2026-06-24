## ADDED Requirements

### Requirement: Emit overlaps-with relations for meaningful partial overlap
The relate stage SHALL emit an `overlaps-with` relation between two documents whose pairwise
embedding similarity falls in the band below the duplicate threshold and at or above a configured
overlap threshold, recording the similarity as evidence. Documents at or above the duplicate
threshold SHALL continue to be related as `duplicate-of`, not `overlaps-with`. The overlap threshold
SHALL be recorded in the run-manifest.

#### Scenario: Partial overlap is surfaced as overlaps-with
- **WHEN** two documents have a confirmed similarity at or above the overlap threshold but below the
  duplicate threshold
- **THEN** an `overlaps-with` relation is recorded between them with the similarity as evidence
- **AND** neither is marked as a duplicate of the other

#### Scenario: Above the duplicate threshold stays duplicate-of
- **WHEN** two documents have a confirmed similarity at or above the duplicate threshold
- **THEN** they are related as `duplicate-of`, not `overlaps-with`
