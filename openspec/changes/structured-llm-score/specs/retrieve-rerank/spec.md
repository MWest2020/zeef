## MODIFIED Requirements

### Requirement: LLM relevance scoring output and degradation
When an LLM is available, the system SHALL obtain each top-K candidate's relevance score (0-100,
normalised to a 0..1 `llm_relevance`) and a one-line rationale using guaranteed structured output
where the active backend supports it, and SHALL fall back to parsing free text otherwise. Backend
support SHALL be advertised explicitly via a capability protocol (`StructuredLLMProvider`), not
inferred implicitly, so that the reason a backend takes the structured route is inspectable. The
`LLMProvider.complete` contract SHALL remain unchanged; structured support is an additive
capability.

Degradation SHALL be three explicit tiers and SHALL never crash: (1) structured JSON when the
backend supports it and returns a valid object; (2) regex parsing of a free-text answer when the
backend is not structured, returns nothing valid, or the object is invalid; (3) a score of 0.0
with the raw answer retained as the rationale when no score can be parsed. The 0..1 score
semantics, the top-K demotion of unscored candidates, and the `--no-llm` skip SHALL be unchanged.

#### Scenario: Structured backend yields a guaranteed-parseable score
- **WHEN** scoring runs and the LLM backend satisfies the structured-output capability
- **THEN** the document's score and rationale come from a validated structured object
- **AND** the score is normalised to 0..1 as the final selection score for that document

#### Scenario: Non-structured backend falls back to regex
- **WHEN** the LLM backend does not satisfy the structured-output capability
- **THEN** scoring parses the free-text answer with the existing regex
- **AND** the resulting score and rationale are identical in form to the prior behaviour

#### Scenario: Invalid structured response falls back without crashing
- **WHEN** a structured backend returns no valid object (e.g. missing required fields)
- **THEN** scoring falls back to regex parsing of a free-text answer
- **AND** if that also yields no score, the document scores 0.0 with the raw answer as rationale

#### Scenario: No-LLM run is unaffected
- **WHEN** the run uses `--no-llm`
- **THEN** the scoring stage is skipped entirely and no structured or regex call is made

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
