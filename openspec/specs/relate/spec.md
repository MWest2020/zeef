# relate Specification

## Purpose
TBD - created by archiving change converge-mvp. Update Purpose after archive.
## Requirements
### Requirement: Mail-thread reconstruction from headers
The system SHALL reconstruct mail threads deterministically from the `Message-ID`,
`In-Reply-To`, and `References` headers, linking replies to their parent via a `thread-parent`
relation. When the required headers are absent, the system MAY fall back to a heuristic but
SHALL mark such relations as heuristic in their evidence.

#### Scenario: Five-message thread forms one cluster
- **WHEN** five emails forming a single reply chain are ingested with intact threading headers
- **THEN** they are linked into one thread cluster via `thread-parent` relations
- **AND** the cluster is treated as one unit for selection, not five independent hits

#### Scenario: Missing headers degrade transparently
- **WHEN** emails lack threading headers
- **THEN** any inferred thread relations carry evidence marking them as heuristic

### Requirement: Near-duplicate and exact-duplicate detection
The relate stage (early in the pipeline) SHALL **detect and relate** duplicates without collapsing
them: exact duplicates via the content-addressed id and near-duplicates via MinHash candidate
generation confirmed by cosine of the **whole-document** embeddings above a configured threshold,
each recorded as a `duplicate-of` relation. Relate SHALL NOT choose a representative and SHALL NOT
remove any document — collapsing a duplicate group to a single representative is the **select**
stage's responsibility, performed after ranking (see the `select` capability). Duplicates SHALL NOT
be silently dropped at any stage; the `duplicate-of` relation keeps every copy inspectable.

#### Scenario: Duplicates are linked but not collapsed in relate
- **WHEN** the relate stage runs over the corpus
- **THEN** each duplicate is linked to its group by a `duplicate-of` relation
- **AND** relate neither chooses a representative nor removes any document (that happens in select)

#### Scenario: Near-duplicate confirmed by whole-document cosine
- **WHEN** two documents are MinHash candidates and their whole-document embedding cosine exceeds
  the threshold
- **THEN** they are linked by a `duplicate-of` relation with the cosine value as evidence

#### Scenario: Duplicates remain visible, not dropped
- **WHEN** a duplicate is later collapsed out of the ranking by select
- **THEN** it is still present as a related document with a logged reason, not removed from the run

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

