## MODIFIED Requirements

### Requirement: Live progress during long per-item stages

When observation is enabled, the long-running per-item loops SHALL report incremental progress to the console while they run, so a run can be followed live during slow stages instead of appearing frozen. This applies to the ingest file-loading loop, the `relate` near-duplicate embedding, the retrieve stage's per-candidate embed loop, and the query-less `embed_chunks` loop used by the discover route.

Progress updates SHALL be emitted at a readable interval — a bounded number of updates,
not one line per document — so a redirected observe log stays readable and `tail`-friendly.
Each update SHALL name the stage and show the processed-count out of the total (e.g.
`retrieve: embedded 200/868`). When observation is disabled the reporting MUST be a no-op:
it MUST perform no console writes and add no audit events. Progress reporting MUST NOT
change ranking, selection, or any exported artifact.

For stages that embed the corpus in a single batch call (notably `relate`), the progress SHALL
originate inside the embedding provider, which SHALL accept an optional progress callback and
invoke it as it works through the input list. The provider's observable contract SHALL be
unchanged: `embed(texts)` still returns one vector per input in original order, and omitting the
callback SHALL leave behaviour identical to before.

#### Scenario: Progress visible during retrieve

- **WHEN** observation is enabled and the retrieve stage embeds a corpus of many
  candidates
- **THEN** the console receives one or more progress updates naming the stage and the
  processed-count out of the total before the stage's completion panel is printed

#### Scenario: Progress visible during ingest

- **WHEN** observation is enabled and the ingest stage loads many files
- **THEN** the console receives one or more progress updates naming the stage and the
  processed-count out of the total before the ingest completion panel is printed

#### Scenario: Progress visible during relate

- **WHEN** observation is enabled and the relate stage embeds the corpus for near-duplicate
  confirmation
- **THEN** the console receives one or more progress updates naming the relate stage and the
  processed-count out of the total before the relate completion panel is printed

#### Scenario: Bounded update volume

- **WHEN** observation is enabled and the retrieve stage embeds N candidates
- **THEN** the number of progress updates is bounded (independent of N beyond the chosen
  interval) so the output does not grow one line per document for large N

#### Scenario: No progress output when disabled

- **WHEN** observation is disabled and an embedding loop runs
- **THEN** no progress updates are written to the console and no progress-related audit
  events are added

#### Scenario: Progress does not affect results

- **WHEN** the same run is executed once with observation enabled and once disabled
- **THEN** `audit.jsonl`, the inventory, and the selection are identical between the two
