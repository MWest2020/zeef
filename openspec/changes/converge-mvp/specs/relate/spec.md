## ADDED Requirements

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
The system SHALL detect exact duplicates via the content-addressed id and near-duplicates via
MinHash/SimHash candidate generation confirmed by embedding cosine above a configured threshold,
recording each as a `duplicate-of` relation. Duplicate documents SHALL NOT be counted twice in
the final selection.

#### Scenario: Identical documents linked, counted once
- **WHEN** two documents with identical content are ingested
- **THEN** they are linked by a `duplicate-of` relation
- **AND** only one of them occupies a slot in the final selection

#### Scenario: Near-duplicate confirmed by cosine
- **WHEN** two documents are MinHash candidates and their embedding cosine exceeds the threshold
- **THEN** they are linked by a `duplicate-of` relation with the cosine value as evidence
