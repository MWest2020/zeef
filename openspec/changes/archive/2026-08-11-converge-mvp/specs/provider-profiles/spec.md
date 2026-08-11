## ADDED Requirements

### Requirement: Profile selects providers without code change
The system SHALL select its `LLMProvider`, `EmbeddingProvider`, and `RerankerProvider`
implementations from a profile chosen with `--profile {cloud,sovereign}`. The pipeline stages
SHALL receive providers by injection and SHALL NOT import concrete drivers directly. Switching
between `cloud` and `sovereign` SHALL require only the flag, no code change.

#### Scenario: Same pipeline, different drivers
- **WHEN** the same converge command is run once with `--profile cloud` and once with
  `--profile sovereign`
- **THEN** both runs execute the identical pipeline, differing only in the resolved providers

#### Scenario: Sovereign makes no external network calls
- **WHEN** a run uses `--profile sovereign`
- **THEN** no provider call leaves the local machine (default-deny egress)

### Requirement: No-LLM fallback
The system SHALL support a `--no-llm` flag that replaces the LLM provider with a null
implementation, causes the scope-filter to use rules only, and causes selection to rely on
embedding and rerank scores only. A `--no-llm` run SHALL complete without invoking any
generative model.

#### Scenario: Generative steps skipped
- **WHEN** a run uses `--no-llm`
- **THEN** no LLM completion is requested and the run still produces a selection

### Requirement: Secrets never in code or config files
Cloud provider credentials SHALL be read from environment variables or a SOPS+age reference and
SHALL NOT appear in source code or committed configuration files.

#### Scenario: Cloud key sourced from environment
- **WHEN** the `cloud` profile needs an API key
- **THEN** it is read from the environment, not from a config file in the repository
