# scope-filter Specification

## Purpose
TBD - created by archiving change converge-mvp. Update Purpose after archive.
## Requirements
### Requirement: Rules-first out-of-scope exclusion
The system SHALL classify a document's **process role** with an ordered set of deterministic rules
and mark out-of-scope material before invoking any LLM. The process roles are: doorstuurmail
(forward-only mail), agendaverzoek (calendar invite), procesmelding (process notification), eerdere
mail al vertegenwoordigd door de thread-head (an earlier mail already represented by its thread
head), and dubbeling (a duplicate). Each matched document SHALL receive `decision = out_of_scope`
and a human-readable `decision_reason` naming the role. This process-role axis SHALL be **orthogonal
to theme**: the scope-filter SHALL NOT emit a theme cluster, and the theme remainder bucket "Overig"
SHALL NEVER be equated with "buiten reikwijdte". A document MAY be on-theme and out-of-scope, or
off-theme and in-scope.

#### Scenario: Process role excludes a calendar invite
- **WHEN** a document matches the agendaverzoek (calendar-invite) rule
- **THEN** its decision is set to `out_of_scope` with a reason naming the role
- **AND** no LLM call is made for that document

#### Scenario: Role and theme stay separate
- **WHEN** a document is on-theme for the query but is a doorstuurmail (forward-only)
- **THEN** it is marked `out_of_scope` by its process role
- **AND** this is recorded as a process-role exclusion, not as a theme ("Overig") assignment

#### Scenario: Every exclusion is justified
- **WHEN** any document is excluded by the scope-filter
- **THEN** it carries a non-empty `decision_reason` naming the process role

### Requirement: LLM fallback only for undecided edge cases
The system SHALL send to the LLM only those documents that no deterministic rule decided, and
only when an LLM provider is available (not in `--no-llm` runs). The LLM decision SHALL be
recorded with its `decision_reason` and an audit event containing the exact prompt.

#### Scenario: Only residue reaches the LLM
- **WHEN** the rule set decides a subset of documents
- **THEN** only the remaining undecided documents are passed to the LLM

#### Scenario: No-LLM run skips the fallback
- **WHEN** the run uses `--no-llm`
- **THEN** documents undecided by the rules remain `undecided` for retrieval rather than being
  sent to an LLM

