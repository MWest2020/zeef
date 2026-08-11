# select Specification

## Purpose
TBD - created by archiving change converge-mvp. Update Purpose after archive.
## Requirements
### Requirement: Three configurable cutoff modes
The system SHALL support three mutually exclusive selection modes: `--top-n N` (select the N
highest-scoring documents), `--threshold X` (select all documents with final score ≥ X), and
`--target N` (an adaptive threshold aiming at approximately N documents). Each selected document
SHALL receive `decision = selected` and a `decision_reason` naming the mode and parameter.

#### Scenario: top-n selects a hard count
- **WHEN** the run uses `--top-n 50`
- **THEN** exactly the 50 highest-scoring documents are marked `selected`

#### Scenario: threshold selects by score
- **WHEN** the run uses `--threshold 0.7`
- **THEN** every document with final score ≥ 0.7 is marked `selected`

#### Scenario: target reports the score knee
- **WHEN** the run uses `--target 100`
- **THEN** the selection aims at ~100 documents and reports where the score knee lies so the
  cutoff is a conscious choice rather than a magic number

#### Scenario: Reproducible selection
- **WHEN** the same mode and parameter are run twice on the same scored input
- **THEN** both runs produce an identical selected set

### Requirement: Explicit recall bias
The system SHALL apply a configurable recall bias that, in cases of ties or near-threshold
scores, favors inclusion over exclusion. The active bias SHALL be recorded in the audit-log.

#### Scenario: Near-threshold document included under recall bias
- **WHEN** a document scores just below the cutoff and the recall bias is active
- **THEN** it is included rather than dropped, and the bias is logged as the reason

