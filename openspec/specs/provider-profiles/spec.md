# provider-profiles Specification

## Purpose
TBD - created by archiving change voyage-transport-hardening. Update Purpose after archive.
## Requirements
### Requirement: Cloud embedding and rerank calls respect provider request limits
The cloud `EmbeddingProvider` (`VoyageEmbed`) and `RerankerProvider` (`VoyageReranker`) SHALL
bound every outbound request to the provider's documented per-request limits so that a realistic
corpus does not cause a request to be rejected. They SHALL do so by (a) truncating each input text
to a configured character budget, and (b) splitting an input list that exceeds a configured count
limit or cumulative-character budget into multiple sequential requests.

The providers SHALL preserve their observable contract exactly: `embed(texts)` returns one vector
per input and `rerank(query, docs)` returns one score per document, both in original input order,
with output length equal to input length. The pipeline's selection semantics SHALL therefore be
unchanged by this bounding.

The configured limits SHALL be recorded in the run manifest, and any truncation that actually
removes text SHALL emit an audit event recording how many inputs were truncated and the maximum
original length, so truncation is a visible, traceable variable rather than a silent one.

Rerank batching SHALL be applied **only if** the provider's relevance score is an absolute
per-(query, document) value independent of the other documents in the request; this property
SHALL be verified against the provider documentation before rerank batching is implemented. If the
score is not batch-independent, the reranker SHALL bound a request by truncation alone and SHALL
fail loudly when the candidate set cannot fit a single request, rather than split it.

#### Scenario: Large corpus does not exceed request limits
- **WHEN** an `embed` or `rerank` call is made over a candidate set larger than a single
  provider request allows
- **THEN** the inputs are split into sequential requests, each within the configured count and
  character budgets
- **AND** the call returns one vector/score per input without a provider request being rejected

#### Scenario: Output order preserved across batches
- **WHEN** inputs are split across multiple requests
- **THEN** the returned vectors/scores are reassembled in the original input order
- **AND** the output length equals the input length

#### Scenario: Oversized single input is truncated, not rejected
- **WHEN** a single input text exceeds the configured character budget
- **THEN** that input is truncated to the budget before sending
- **AND** the request is not rejected for that input

#### Scenario: Truncation and limits are auditable
- **WHEN** truncation removes text from at least one input
- **THEN** an audit event records the count of truncated inputs and the maximum original length
- **AND** the configured limits are recorded in the run manifest

#### Scenario: Rerank split only when score independence is verified
- **WHEN** the provider's rerank score is not an absolute per-(query, document) value independent
  of the batch
- **THEN** the reranker bounds the request by per-document truncation only
- **AND** if the candidate set still cannot fit a single request, the call fails loudly rather
  than splitting the documents

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

### Requirement: Default sovereign Ollama embed model

When the sovereign profile uses Ollama embeddings, the system SHALL default the Ollama embed model to `bge-m3:latest`, and this default SHALL be overridable via the `ZEEF_OLLAMA_EMBED_MODEL` environment variable. This is a provisional default chosen on practical grounds (lowest runtime and GPU footprint, and comparable/sharper score spread in an agreement-only comparison on the Woo corpus); it is NOT a claim that bge-m3 selects more relevant documents, and the final default awaits a ground-truth (recall) measurement.

Changing this default SHALL NOT change the sovereign profile's default embedder: with no `ZEEF_SOVEREIGN_EMBED=ollama` opt-in, the sovereign profile MUST still resolve the deterministic, air-gapped local embedder (no server or weights required).

#### Scenario: Ollama opt-in uses bge-m3 by default

- **WHEN** the sovereign profile is resolved with `ZEEF_SOVEREIGN_EMBED=ollama` and no
  `ZEEF_OLLAMA_EMBED_MODEL` set
- **THEN** the embedding provider is Ollama with model `bge-m3:latest`

#### Scenario: Env-var overrides the default

- **WHEN** `ZEEF_OLLAMA_EMBED_MODEL` is set (e.g. `qwen3-embedding:0.6b`) with
  `ZEEF_SOVEREIGN_EMBED=ollama`
- **THEN** the embedding provider uses the env-var model, not the default

#### Scenario: Default sovereign stays air-gapped

- **WHEN** the sovereign profile is resolved without `ZEEF_SOVEREIGN_EMBED=ollama`
- **THEN** the embedding provider is the deterministic local embedder, requiring no server or
  network

