## MODIFIED Requirements

### Requirement: Three configurable cutoff modes
The system SHALL select documents by cutting the **relevance ranking** (the query-cosine order,
see `relevance-ranking`) in one of three mutually exclusive modes: `--top-n N` (the N
highest-relevance documents), `--threshold X` (all documents with relevance ≥ X), and `--target N`
(an adaptive threshold aiming at approximately N documents). The selection SHALL be fixed and
serialized **before** any report or UI is produced, so the top-N is one documented, reproducible
choice independent of what a user later clicks. Each selected document SHALL receive `decision =
selected` and a `decision_reason` naming the mode and parameter.

#### Scenario: top-n selects a hard count of representatives
- **WHEN** the run uses `--top-n 100`
- **THEN** exactly the 100 highest-ranked **representatives** are marked `selected` (duplicate
  groups already collapsed to one representative each), so the output is ~100 distinct documents

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

## ADDED Requirements

### Requirement: Collapse duplicate groups after ranking; the top-N counts representatives
The **select** stage SHALL own the duplicate-collapse (relate only detects and relates, see the
`relate` capability). The order SHALL be: rank the **full candidate set including duplicates** by
the passage-cosine `final` score → within each `duplicate-of` group keep the **highest-ranked**
member as the representative and collapse the rest with a logged reason → take the top-N over the
**representatives**. Ties on relevance SHALL be broken by a query-independent stable key (ingestion
order or source path), since exact duplicates share a content-addressed id. The result SHALL
therefore be N distinct representatives (≈100 documents), never "rank the top-N then dedup down to
fewer than N".

#### Scenario: The top-N is N representatives, not N-minus-duplicates
- **WHEN** the candidate set contains duplicate groups and the run uses `--top-n 100`
- **THEN** the full set is ranked, each duplicate group is collapsed to its highest-ranked
  representative, and the 100 highest-ranked representatives are selected
- **AND** the output contains ~100 distinct documents, not fewer because duplicates ate slots

#### Scenario: The representative is the highest-ranked member with a query-independent tiebreak
- **WHEN** a duplicate group is collapsed at select
- **THEN** its representative is the highest-ranked member; ties are broken by ingestion order /
  source path, not by the shared content-addressed id
- **AND** the collapsed copies are logged with a reason and remain linked by `duplicate-of`
