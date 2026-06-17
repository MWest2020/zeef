## ADDED Requirements

### Requirement: Rules-first out-of-scope exclusion
The system SHALL apply an ordered set of deterministic rules to exclude out-of-scope material
(e.g. forwarded-only mail, calendar invites, process notifications, earlier mails already
represented by a thread head, duplicates) before invoking any LLM. Each excluded document SHALL
receive `decision = out_of_scope` and a human-readable `decision_reason`.

#### Scenario: Rule excludes a calendar invite
- **WHEN** a document matches the calendar-invite rule
- **THEN** its decision is set to `out_of_scope` with a reason naming the rule
- **AND** no LLM call is made for that document

#### Scenario: Every exclusion is justified
- **WHEN** any document is excluded by the scope-filter
- **THEN** it carries a non-empty `decision_reason`

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
