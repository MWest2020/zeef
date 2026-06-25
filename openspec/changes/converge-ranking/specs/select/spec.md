## MODIFIED Requirements

### Requirement: Three configurable cutoff modes
The system SHALL select documents by cutting the **relevance ranking** (the query-cosine order,
see `relevance-ranking`) in one of three mutually exclusive modes: `--top-n N` (the N
highest-relevance documents), `--threshold X` (all documents with relevance ≥ X), and `--target N`
(an adaptive threshold aiming at approximately N documents). The selection SHALL be fixed and
serialized **before** any report or UI is produced, so the top-N is one documented, reproducible
choice independent of what a user later clicks. Each selected document SHALL receive `decision =
selected` and a `decision_reason` naming the mode and parameter.

#### Scenario: top-n selects a hard count by relevance
- **WHEN** the run uses `--top-n 100`
- **THEN** exactly the 100 highest-relevance documents are marked `selected`

#### Scenario: target reports the score knee
- **WHEN** the run uses `--target 100`
- **THEN** the selection aims at ~100 documents and reports where the relevance knee lies so the
  cutoff is a conscious choice rather than a magic number

#### Scenario: Selection is fixed before any UI
- **WHEN** a run completes the select stage
- **THEN** the selected set is serialized from the ranking alone
- **AND** no later report, clustering or UI interaction can change which documents are selected

#### Scenario: The cut ranks the full candidate set
- **WHEN** the select stage cuts the top-N
- **THEN** it ranks every candidate by its passage-cosine `final` score
- **AND** no candidate was demoted or excluded by a rerank/LLM pass before the cut (no hidden
  recall-gate)

#### Scenario: Reproducible selection
- **WHEN** the same mode and parameter are run twice on the same ranked input
- **THEN** both runs produce an identical selected set

### Requirement: Explicit recall bias
The system SHALL apply a configurable recall bias that, in cases of ties or near-threshold
relevance scores, favors inclusion over exclusion. The bias SHALL operate only on the relevance
ranking at the cutoff and SHALL be recorded in the audit-log. The bias SHALL NOT use cluster
membership or process role to include or exclude a document.

#### Scenario: Near-threshold document included under recall bias
- **WHEN** a document scores just below the cutoff and the recall bias is active
- **THEN** it is included rather than dropped, and the bias is logged as the reason

#### Scenario: Bias never appeals to clusters
- **WHEN** the recall bias decides a near-threshold case
- **THEN** the decision is based on the relevance score only, not on the document's theme cluster
