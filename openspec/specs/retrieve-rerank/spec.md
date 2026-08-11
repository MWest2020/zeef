# retrieve-rerank Specification

## Purpose
TBD - created by archiving change converge-mvp. Update Purpose after archive.
## Requirements
### Requirement: Chunk and embed documents
The system SHALL chunk long documents and embed them through an `EmbeddingProvider`, storing
embeddings on the chunks. Chunking SHALL be deterministic for a given document and chunk size.

#### Scenario: Long document is chunked before embedding
- **WHEN** a document exceeds the configured chunk size
- **THEN** it is split into ordered chunks and each chunk receives an embedding

### Requirement: First-pass retrieval against the refined query
The system SHALL produce first-pass candidates by similarity of the refined query to document
embeddings, optionally combined with a BM25 lexical score (hybrid). The first-pass similarity
SHALL be recorded in `Document.scores` (e.g. `embed_sim`).

#### Scenario: Query retrieves candidates with recorded scores
- **WHEN** retrieval runs for a query
- **THEN** each candidate document has an `embed_sim` score in its `scores` dict

### Requirement: Precision rerank pass
The system SHALL rerank the first-pass candidates through a `RerankerProvider` (cross-encoder or
LLM-as-reranker) and record the rerank score in `Document.scores`. The reranked score SHALL feed
the final selection score.

#### Scenario: Rerank refines the ordering
- **WHEN** rerank runs over the first-pass candidates
- **THEN** each candidate gains a `rerank` score and the candidates are reordered by it

