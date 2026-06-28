# observe Specification

## Purpose
Live, leesbare terminalweergave van een run (`--observe` / `ZEEF_OBSERVE=1`): per stap één
paneel uit de audit-trail, plus voortgangstellers tijdens de lange per-item stappen, zodat een
run te volgen is zonder de pijplijn-logica of de resultaten te raken.
## Requirements
### Requirement: Per-stage observation panels

When observation is enabled (the `--observe` flag or `ZEEF_OBSERVE=1`), the system SHALL
render exactly one human-readable panel per pipeline stage after that stage completes,
derived solely from the audit events the stage already wrote. Observation SHALL NOT alter
pipeline logic, ranking, selection, or any exported artifact, and SHALL be a no-op when
disabled.

#### Scenario: Observation disabled by default

- **WHEN** a run is started without `--observe` and without `ZEEF_OBSERVE=1`
- **THEN** no observation panels or progress lines are printed
- **AND** the run's artifacts are byte-identical to a run with observation enabled

#### Scenario: One panel per completed stage

- **WHEN** observation is enabled and a stage completes
- **THEN** the system prints one panel for that stage showing INPUT, OUTPUT, KEUZE, and
  HERKOMST, built only from that stage's audit events

#### Scenario: Criteria panel shows the actual query

- **WHEN** observation is enabled and criteria falls back to the raw query (`--no-llm`)
- **THEN** the criteria panel's INPUT shows a prefix of the actual query text, not only
  the literal word "zoekvraag"

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

