## MODIFIED Requirements

### Requirement: Precision rerank pass
The system SHALL rerank the first-pass candidates through a `RerankerProvider` (cross-encoder or
LLM-as-reranker) and record the rerank score in `Document.scores`. The rerank ordering SHALL
bound which candidates reach LLM relevance scoring (the top-K pre-trim). When no LLM is available
(`--no-llm`) the rerank score SHALL feed the final selection score, preserving the deterministic
run.

#### Scenario: Rerank refines the ordering
- **WHEN** rerank runs over the first-pass candidates
- **THEN** each candidate gains a `rerank` score and the candidates are reordered by it

#### Scenario: No-LLM run selects on the rerank score
- **WHEN** the run uses `--no-llm`
- **THEN** the rerank score is used as the final selection score (no LLM scoring runs)

## ADDED Requirements

### Requirement: LLM relevance scoring against the criteria, with a rationale
When an LLM is available, the system SHALL score the top-K reranked candidates against the
articulated criteria, producing for each scored document a graded relevance score in
`Document.scores` (e.g. `llm_relevance`) and a human-readable rationale on the document. The
graded relevance score SHALL become the final selection score for scored documents. Each score
SHALL be recorded in the audit-log with the exact prompt, model and location.

#### Scenario: Scored document gains a graded score and a rationale
- **WHEN** relevance scoring runs over the reranked candidates with an LLM available
- **THEN** each scored document has a graded `llm_relevance` score and a non-empty rationale
- **AND** its final selection score equals the graded relevance score
- **AND** an audit event records the exact prompt, model and location

### Requirement: Bounded scoring with no silent coverage cap
The system SHALL bound LLM scoring to the top-K reranked candidates (K configurable via
`--score-top-k`; `0` means score every candidate). Candidates outside the scored set SHALL be
demoted out of selection contention with a recorded reason rather than silently dropped, and the
number scored versus demoted SHALL be logged.

#### Scenario: Candidates beyond top-K are demoted, not silently dropped
- **WHEN** scoring runs with a finite `--score-top-k` smaller than the candidate count
- **THEN** only the top-K reranked candidates are LLM-scored
- **AND** the remaining candidates are demoted below the scored ones with a recorded reason
- **AND** the count scored versus demoted is recorded in the audit-log
