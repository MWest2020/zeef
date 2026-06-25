## MODIFIED Requirements

### Requirement: Sovereign lexical reranker scoring
The sovereign lexical reranker SHALL produce a per-document relevance score against the query
using a vendored, well-understood BM25 implementation (`rank_bm25.BM25Okapi`) rather than a
hand-written scoring loop. The reranker SHALL preserve its observable contract exactly:
`rerank(query: str, docs: list[str]) -> list[float]` returns one score per document in input
order, every score normalised to the range 0..1, an empty `docs` list returns `[]`, and the
computation SHALL be fully deterministic, require no network, and require no model weights
(air-gapped, pure Python).

The reranker SHALL feed query terms to BM25 **deduplicated** — each distinct query term counts
exactly once — so that a repeated query term cannot silently change the ordering. The negative-idf
floor (`epsilon`) SHALL be passed explicitly so that all score contributions remain non-negative
and the 0..1 normalisation cannot emit a negative value.

#### Scenario: Contract preserved after the library swap
- **WHEN** `rerank(query, docs)` is called over a non-empty candidate set
- **THEN** the result has one value per document, in input order
- **AND** every value lies in 0.0..1.0
- **AND** the same input produces the same output on every run, with no network access

#### Scenario: Empty candidate set
- **WHEN** `rerank(query, [])` is called
- **THEN** the result is `[]`

#### Scenario: Repeated query terms do not double-count
- **WHEN** a query contains a repeated token (e.g. "begroting begroting cultuur")
- **THEN** the resulting ordering equals the ordering for the same query with the token appearing
  once ("begroting cultuur")

#### Scenario: High-document-frequency term stays defensible
- **WHEN** a query term appears in more than half of the candidate documents (negative standard
  Okapi idf, floored by `epsilon`)
- **THEN** scores remain non-negative and within 0..1
- **AND** a document that also contains a rarer, discriminating query term ranks above a document
  that contains only the common term

#### Scenario: Rerank still refines the first-pass ordering (regression)
- **WHEN** rerank runs over candidates where the lexical signal disagrees with term-frequency
  concentration (query "beta gamma": "d2" carries distinct query terms across a longer document,
  "d1" repeats a single term)
- **THEN** "d2" ranks above "d1"
