## MODIFIED Requirements

### Requirement: LLM relevance scoring against the criteria, with a rationale
The system SHALL treat any LLM relevance score as a side-score and the rationale as the optional,
clearly-labelled "why" gloss; the LLM stage SHALL NOT write the `final` score and SHALL NOT demote
or exclude any candidate (design D14/D22/D23). When an LLM is available the system MAY score each
candidate against the articulated criteria (0-100, normalised to a 0..1 `llm_relevance`) and
attach a one-line rationale, obtained via guaranteed structured output where the active backend
supports it and free-text parsing otherwise. Backend support SHALL be advertised explicitly via a
capability protocol (`StructuredLLMProvider`), not inferred implicitly, so the reason a backend
takes the structured route is inspectable; the `LLMProvider.complete` contract SHALL remain
unchanged (structured support is an additive capability). Each such call SHALL be recorded in the
audit-log with the exact prompt, model and location.

Degradation SHALL be three explicit tiers and SHALL never crash: (1) structured JSON when the
backend supports it and returns a valid object; (2) regex parsing of a free-text answer when the
backend is not structured, returns nothing valid, or the object is invalid; (3) a score of 0.0
with the raw answer retained as the rationale when no score can be parsed. The `--no-llm` skip
SHALL be unchanged; because the LLM score is a side-score, an unscored or 0.0 candidate SHALL NOT
be demoted or removed — its `final` remains the passage cosine.

#### Scenario: LLM score enriches but neither selects nor demotes
- **WHEN** LLM relevance scoring runs with an LLM available
- **THEN** each scored document gains a rationale used only as a labelled "why" gloss
- **AND** the `final` score remains the passage cosine for every candidate
- **AND** no candidate is demoted to `0.0` or removed from the ranking
- **AND** an audit event records the exact prompt, model and location

#### Scenario: Structured backend yields a guaranteed-parseable score
- **WHEN** scoring runs and the LLM backend satisfies the structured-output capability
- **THEN** the document's `llm_relevance` and rationale come from a validated structured object

#### Scenario: Non-structured backend falls back to regex
- **WHEN** the LLM backend does not satisfy the structured-output capability
- **THEN** scoring parses the free-text answer with the existing regex
- **AND** the resulting score and rationale are identical in form to the prior behaviour

#### Scenario: Invalid structured response falls back without crashing
- **WHEN** a structured backend returns no valid object (e.g. missing required fields)
- **THEN** scoring falls back to regex parsing of a free-text answer
- **AND** if that also yields no score, the document scores 0.0 with the raw answer as rationale

#### Scenario: No-LLM run selects identically on the cosine
- **WHEN** the run uses `--no-llm`
- **THEN** the `final` score is the passage cosine for every candidate (not a rerank/BM25 score)
- **AND** no rationale is produced and no LLM call is made

## ADDED Requirements

### Requirement: Auditability of the structured scoring path
The structured-output scoring path SHALL be at least as auditable as the regex path it replaces.
Each structured score event SHALL record, in addition to the exact prompt, model and location, the
JSON schema sent to the backend and the raw structured response returned by the backend (before
normalisation). The regex path SHALL continue to record the exact prompt and the free-text answer.

#### Scenario: Structured score event carries schema and raw response
- **WHEN** a document is scored via the structured path
- **THEN** the audit event records the exact prompt, model, location, the JSON schema, and the raw
  structured response
- **AND** the normalised score and rationale derived from it are also recorded
