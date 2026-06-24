## 1. Ingest health metadata
- [x] 1.1 `char_count` on metadata
- [x] 1.2 `parse_ok` (false on failure; still produce a `Document`, do not drop)
- [x] 1.3 `redaction_ratio` from redaction markers (shared `health.py`)
- [x] 1.4 Tests: usable / unparseable / low-text-not-redacted / low-text-redacted

## 2. Config
- [x] 2.1 `validity_min_chars` + `redaction_ratio_threshold` (conservative defaults)
- [x] 2.2 Recorded in manifest params

## 3. Stage
- [x] 3.1 `pipeline/validity.py`: `validity_gate(docs, audit, *, min_chars, redaction_ratio_threshold) -> docs`
- [x] 3.2 Order parse_ok → empty-after-OCR (redaction-aware) → language (soft)
- [x] 3.3 Hard failure → `out_of_scope` + `validity:<reason>` + audit event
- [x] 3.4 Redaction-aware keep + flag (stays `undecided`)

## 4. Wiring
- [x] 4.1 `run.py`: stage between `ingest` and `relate`, inside the timer
- [x] 4.2 Recorded in manifest timings (via `run_stage`)

## 5. Reporting
- [x] 5.1 `cli.py` validity count shown separately
- [x] 5.2 `validity_excluded` count distinct from `out_of_scope`

## 6. Tests / verification
- [x] 6.1 Unusable excluded with the right reason; usable unchanged through the gate
- [x] 6.2 Redacted kept + flagged
- [x] 6.3 `openspec validate --strict`
- [x] 6.4 `uv run pytest` green; `ruff` clean
