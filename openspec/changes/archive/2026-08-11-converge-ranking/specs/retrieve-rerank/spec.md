## MODIFIED Requirements

### Requirement: First-pass retrieval against the refined query
The system SHALL compute relevance as the **maximum cosine of the document's chunk embeddings to the
query embedding** (the best-matching passage), and SHALL set this as the `final` score on **every**
candidate (alongside a recorded `embed_sim`/`relevance`). This passage-level cosine — not a
whole-document embedding — is the relevance signal and the input to selection (design D15);
whole-document relevance is recorded as a rejected, recall-inferior alternative. The audit rule is
one sentence: *cosine of the best-matching passage to the query.*

#### Scenario: Query scores each candidate by its best passage, as `final`
- **WHEN** retrieval runs for a refined query
- **THEN** each candidate's `final` score equals the maximum cosine of its chunk embeddings to the
  query (the best-matching passage)

#### Scenario: Relevance is passage-level, not whole-document
- **WHEN** a long document is relevant only in one passage
- **THEN** its relevance reflects that passage's cosine and is not averaged away across the document

### Requirement: Precision rerank pass
The cross-encoder/LLM rerank pass SHALL NOT be the selector and SHALL NOT write the `final` score.
When a `RerankerProvider` is present it MAY record a `rerank` score as a **side-score** for
inspection only; the documented, reproducible selection is driven by the relevance ranking
(`relevance-ranking`). In the sovereign profile, which has no reranker model, no rerank pass is
required for selection.

#### Scenario: Rerank records a side-score and does not touch `final`
- **WHEN** a rerank pass runs over the candidates
- **THEN** any `rerank` score is recorded for inspection only
- **AND** the `final` score remains the passage cosine, unchanged by rerank

### Requirement: LLM relevance scoring against the criteria, with a rationale
The system SHALL treat any LLM relevance score as a side-score and the rationale as the optional,
clearly-labelled "why" gloss; the LLM stage SHALL NOT write the `final` score and SHALL NOT demote
or exclude any candidate (design D14/D22/D23). When an LLM is available the system MAY score
documents against the articulated criteria and attach a rationale, and SHALL record each such call
in the audit-log with the exact prompt, model and location.

#### Scenario: LLM score enriches but neither selects nor demotes
- **WHEN** LLM relevance scoring runs with an LLM available
- **THEN** each scored document gains a rationale used only as a labelled "why" gloss
- **AND** the `final` score remains the passage cosine for every candidate
- **AND** no candidate is demoted to `0.0` or removed from the ranking
- **AND** an audit event records the exact prompt, model and location

#### Scenario: No-LLM run selects identically on the cosine
- **WHEN** the run uses `--no-llm`
- **THEN** the `final` score is the passage cosine for every candidate (not a rerank/BM25 score)
- **AND** no rationale is produced and no LLM call is made
