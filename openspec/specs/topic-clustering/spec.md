# topic-clustering Specification

## Purpose
TBD - created by archiving change topic-clustering. Update Purpose after archive.
## Requirements
### Requirement: Group the selected core into a two-level topic structure
The system SHALL, after the select stage, group the selected documents into a two-level structure
of onderwerp (coarse) and deelonderwerp (fine, nested within an onderwerp) using deterministic
clustering over the documents' embeddings. The grouping SHALL be reproducible: the clustering
parameters SHALL be recorded in the run-manifest, and an identical run SHALL produce an identical
grouping. Each selected document SHALL be assigned exactly one onderwerp and one deelonderwerp.
When a document's chunks fall into more than one cluster, the system SHALL assign the document by
majority vote over its chunk memberships — the onderwerp where most of its chunks fall, and the
majority deelonderwerp within that onderwerp — breaking ties deterministically. This rule SHALL be
deterministic so the assignment is reproducible.

#### Scenario: Selected documents are grouped reproducibly
- **WHEN** the topic-clustering stage runs over the selected core
- **THEN** each selected document is assigned one onderwerp and one deelonderwerp
- **AND** the clustering parameters used are recorded in the run-manifest

#### Scenario: A document whose chunks span clusters gets one topic by majority
- **WHEN** a document's chunk embeddings fall into more than one cluster
- **THEN** the document is assigned the single onderwerp where the majority of its chunks fall, and
  one deelonderwerp within that onderwerp
- **AND** the assignment is deterministic across identical runs

#### Scenario: Small clusters collapse into a remainder bucket
- **WHEN** a cluster contains fewer documents than the configured minimum cluster size
- **THEN** its documents are assigned to a single deterministic "Overig" onderwerp
- **AND** the collapse is recorded in the audit-log

### Requirement: Label topics with the LLM, with a deterministic fallback
The system SHALL label each onderwerp and deelonderwerp with a short human-readable Dutch label
using an `LLMProvider`, recording the exact prompt, model and location in the audit-log. When no
LLM is available (`--no-llm`), the system SHALL produce deterministic labels from the cluster's
most distinctive terms, marked as a fallback, and SHALL make no LLM call.

#### Scenario: Clusters are labelled by the LLM
- **WHEN** topic labelling runs with an LLM available
- **THEN** each onderwerp and deelonderwerp receives a human-readable label
- **AND** an audit event records the exact prompt, the model and its location per labelled cluster

#### Scenario: No-LLM run falls back to deterministic labels
- **WHEN** topic labelling runs under `--no-llm`
- **THEN** each onderwerp and deelonderwerp receives a term-based label marked as a fallback
- **AND** no LLM call is made

### Requirement: Export the topic structure as a navigable menu
The system SHALL write a `topics.json` artifact to the run output directory mapping each onderwerp
to its deelonderwerpen and each deelonderwerp to the list of document ids it contains, including
the labels. This artifact SHALL be sufficient on its own to present the selection to a requester as
a navigable menu over the selected core.

#### Scenario: topics.json is written for a run
- **WHEN** a convergence run with topic-clustering completes
- **THEN** a `topics.json` file is present in the run output directory
- **AND** it maps onderwerp → deelonderwerp → document ids with their labels

