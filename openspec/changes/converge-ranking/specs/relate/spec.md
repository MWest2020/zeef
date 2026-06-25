## MODIFIED Requirements

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
