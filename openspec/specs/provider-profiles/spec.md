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

