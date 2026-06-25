## MODIFIED Requirements

### Requirement: Near-duplicate and exact-duplicate detection
The system SHALL detect exact duplicates via the content-addressed id and near-duplicates via
MinHash candidate generation confirmed by cosine of the **whole-document** embeddings above a
configured threshold, recording each as a `duplicate-of` relation. Duplicates SHALL NOT be silently
dropped. Because the representative is chosen by relevance (a query-dependent quantity), the
duplicate-collapse SHALL run **after** the relevance ranking, not before: the relevance ranking is
computed over the full candidate set including duplicates, and then within each duplicate group the
**highest-ranked** member SHALL be the representative that occupies a selection slot while the rest
are collapsed with a logged reason. Ties on relevance SHALL be broken by a **query-independent stable
key** — ingestion order (or source path) — since the content-addressed id cannot break ties between
exact duplicates that share the same hash.

#### Scenario: Representative is the highest-ranked member, chosen after ranking
- **WHEN** several documents form a duplicate group and the relevance ranking has been computed over
  the full candidate set
- **THEN** the highest-ranked member is the representative that occupies a slot
- **AND** the other members are collapsed with a logged reason and linked by `duplicate-of`

#### Scenario: Exact duplicates get a query-independent tiebreak
- **WHEN** two members of a duplicate group have the same relevance score (e.g. identical content)
- **THEN** the representative is decided by a query-independent stable key (ingestion order / source
  path), not by the shared content-addressed id
- **AND** the choice is deterministic across identical runs

#### Scenario: Near-duplicate confirmed by whole-document cosine
- **WHEN** two documents are MinHash candidates and their whole-document embedding cosine exceeds
  the threshold
- **THEN** they are linked by a `duplicate-of` relation with the cosine value as evidence

#### Scenario: Duplicates remain visible, not dropped
- **WHEN** a duplicate is collapsed out of the ranking
- **THEN** it is still present as a related document with a logged reason, not removed from the run
