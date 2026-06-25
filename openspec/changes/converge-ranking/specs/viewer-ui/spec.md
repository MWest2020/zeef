## MODIFIED Requirements

### Requirement: Present the selected core as a navigable topic menu
The converge report SHALL present the **already-fixed** top-N (the selection serialized by the
ranking before any UI) grouped by onderwerp and deelonderwerp as a collapsible choice-menu,
clustering exactly those selected documents at chunk-level (reuse of `topic-clustering`). The
clustering is navigation only and SHALL NEVER change which documents are shown. The report SHALL
carry the **refined query in its meta** — this artifact is explicitly *about a query*, which
distinguishes it from the discover-report (that carries "zonder zoekvraag"). Per document the report
SHALL show its **relevance score** and a **deterministic "why"** — the best-matching passage (the
chunk that produced the max cosine) plus the query terms it overlaps — alongside its summary (when
present), selection reason, redaction status and relations. The LLM rationale MAY be shown only as a
clearly-labelled, non-load-bearing gloss; on any conflict the deterministic anchor wins (design D23).

#### Scenario: The report is about a query
- **WHEN** a reviewer opens the converge report for a completed run
- **THEN** the refined query is shown in the report meta
- **AND** the report is distinguishable from the discover-report, which carries no query

#### Scenario: A reviewer navigates the fixed selection by topic
- **WHEN** a reviewer opens the report
- **THEN** the selected documents are grouped under onderwerp/deelonderwerp as a menu
- **AND** the grouping is over exactly the fixed top-N and does not change which documents are shown

#### Scenario: Each document shows its relevance and a deterministic why
- **WHEN** a reviewer opens a document in the report
- **THEN** it shows its relevance score and the deterministic "why" (the best-matching passage plus
  the overlapping query terms)
- **AND** any LLM rationale present is shown as a clearly-labelled, non-load-bearing gloss

#### Scenario: Clustering never filters the selection
- **WHEN** a selected document clusters into the "Overig" theme bucket
- **THEN** it is still shown in the report as part of the top-N
- **AND** its theme grouping does not remove it from the selection
