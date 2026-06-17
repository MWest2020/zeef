## ADDED Requirements

### Requirement: Canonical Document model
The system SHALL represent every ingested file as a single `Document` pydantic model carrying
its id, source path, document type, metadata, normalized text, chunks, relations, per-stage
scores, decision, and decision reason. All pipeline stages SHALL read from and write to this
model and SHALL NOT depend on the original file format.

#### Scenario: Heterogeneous inputs share one shape
- **WHEN** an `.eml` file and a digital PDF are ingested
- **THEN** both are represented as `Document` instances with the same fields
- **AND** downstream stages process them identically without format-specific branches

#### Scenario: Scores and decisions accumulate on the document
- **WHEN** a document passes through embed, rerank, and select
- **THEN** its `scores` dict contains the per-stage scores and its `decision` and
  `decision_reason` reflect the final outcome

### Requirement: Content-addressed stable id
The system SHALL derive each `Document.id` deterministically from its normalized text and source
path, such that re-running ingest on the same input yields the same id.

#### Scenario: Reproducible id across runs
- **WHEN** the same file is ingested in two separate runs
- **THEN** both runs assign the document the same `id`

### Requirement: Typed relations between documents
The `Document` model SHALL carry a list of typed `Relation` entries, each with a `kind`
(`thread-parent`, `attachment-of`, `duplicate-of`, `overlaps-with`), a `target_id`, and
human-readable `evidence` for why the relation was asserted.

#### Scenario: Relation records its evidence
- **WHEN** two documents are linked as `duplicate-of`
- **THEN** the relation stores the evidence (e.g. matching content hash or cosine value)
