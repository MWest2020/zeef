## ADDED Requirements

### Requirement: converge command runs the full pipeline
The system SHALL provide a `zeef converge <docs-dir> --query <text>` command (Typer) that runs
ingest → normalize → relate → scope-filter → embed → retrieve → rerank → select → export over a
local folder and writes its outputs to a run directory.

#### Scenario: End-to-end run on a local folder
- **WHEN** `zeef converge ./docs --query "..." --profile sovereign --no-llm` is run on a folder
  of mixed `.eml` and digital PDF files with no network available
- **THEN** the command completes and produces `inventory.xlsx`, `relations.json`, and
  `audit.jsonl`

### Requirement: Selection and profile flags
The command SHALL accept `--profile {cloud,sovereign}`, `--no-llm`, and exactly one of
`--top-n`, `--threshold`, or `--target`. Supplying more than one cutoff flag SHALL be rejected
with a clear error.

#### Scenario: Conflicting cutoff flags rejected
- **WHEN** both `--top-n` and `--target` are supplied
- **THEN** the command exits with an error explaining the modes are mutually exclusive

#### Scenario: Profile switch needs only the flag
- **WHEN** the user changes `--profile sovereign` to `--profile cloud`
- **THEN** the same command runs the same pipeline against cloud providers with no other change

### Requirement: Progress and summary output
The command SHALL present human-readable progress and a final summary (counts selected /
excluded / undecided, output paths) via `rich`, separate from the machine-readable audit-trail.

#### Scenario: Summary shown on completion
- **WHEN** a converge run finishes
- **THEN** the user sees a summary of how many documents were selected and where outputs were
  written
