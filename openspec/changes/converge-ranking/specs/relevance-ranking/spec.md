## ADDED Requirements

### Requirement: Relevance is the best-matching-passage cosine to the query
The system SHALL compute, for each candidate document, a relevance score equal to the **maximum
cosine between the query embedding and the document's chunk embeddings** — the cosine of the
best-matching passage to the query. The score SHALL be recorded as the document's `final` score (and
a named score such as `relevance`/`embed_sim`) for **every** candidate, and SHALL be deterministic
for a given corpus, query, chunk size and embedding model. Relevance is measured at passage
granularity; this is deliberately a different granularity from near-duplicate detection, which uses
whole-document embeddings (design D15).

#### Scenario: Every candidate gets a passage-level relevance score as `final`
- **WHEN** the relevance-ranking stage runs for a refined query
- **THEN** each candidate document's `final` score is the maximum cosine of its chunk embeddings to
  the query embedding (the best-matching passage)

#### Scenario: Relevance is reproducible
- **WHEN** the same corpus, query, chunk size and embedding model are run twice
- **THEN** both runs produce identical relevance scores and an identical ordering

#### Scenario: Relevance and dedup use different granularities
- **WHEN** relevance and near-duplicate detection both run
- **THEN** relevance uses chunk (passage) embeddings while dedup uses whole-document embeddings
- **AND** neither granularity is substituted for the other

### Requirement: The relevance ranking is the sole selector
The system SHALL select documents solely by sorting on the relevance score; cluster membership and
process-role classification SHALL NOT enter the relevance score or the selection. The system SHALL
NOT blend relevance with cluster membership in any weighted form (no `w·nabijheid + (1−w)·
lidmaatschap`, no magic weights). Relevance is the cosine, and nothing else decides membership.

#### Scenario: A document in the theme remainder still ranks on relevance
- **WHEN** a document would cluster into the "Overig" theme bucket but its relevance score places
  it within the top-N
- **THEN** it is selected on relevance, and its theme cluster does not exclude it

#### Scenario: No blended score
- **WHEN** the selection runs
- **THEN** the score driving the cut equals the query cosine alone, with no clustering term mixed in

### Requirement: No hidden recall-gate before the selector
The cosine SHALL rank the **full candidate set**, not a subset that survived an earlier pass. No
stage SHALL demote a candidate's `final` score or exclude it from ranking before the cosine is
applied. The rerank score and the LLM relevance score SHALL be **side-scores** — recorded for
transparency and used only as the "why" — and SHALL NEVER gate which documents are eligible for
selection. (This closes the verified gate where `rerank.py` wrote `final` and `score.py` demoted
non-top-K candidates to `0.0`; design D22.)

#### Scenario: A document that no LLM/rerank pass favoured is still rankable
- **WHEN** a document is not among the rerank or LLM-scored top-K
- **THEN** its `final` score is still its passage cosine and it competes in the full ranking
- **AND** no stage has demoted it to `0.0` or removed it before the cosine ranking

#### Scenario: Side-scores never gate selection
- **WHEN** a rerank score or an LLM relevance score is recorded for a document
- **THEN** that score is kept for transparency/"why" only
- **AND** it does not change which documents are eligible for the top-N

#### Scenario: No-LLM run ranks the full set on cosine
- **WHEN** the run uses `--no-llm`
- **THEN** every candidate's `final` score is its passage cosine to the query
- **AND** the ranking is over the full candidate set with no rerank-based demotion
