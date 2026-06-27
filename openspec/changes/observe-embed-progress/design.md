## Context

`StageObserver` (`observe.py`) is deliberately a pure *reader*: after each stage it reads
the new audit lines that stage wrote and renders one panel. It never reaches into stage
logic. This keeps the audit trail the single source of truth for what is shown.

The retrieve stage (`pipeline/retrieve.py`) embeds every candidate in one loop and writes
its audit event only once, at the end. With a fast local hashing embedder the loop is sub
-second, so the after-the-fact panel is fine. With a remote/slow embedder (Ollama,
Voyage) on ~1000 documents the loop dominates wall-clock and emits nothing while running —
the observer has nothing to render until it finishes, so the run looks frozen. The
discover route's `embed_chunks` has the same shape.

The constraint: add live progress *without* breaking the "observe only reads audit"
property for the panels, without adding 1000 per-document audit events, and without
changing any result.

## Goals / Non-Goals

**Goals:**
- During an embed loop, emit a small number of progress updates to the console when
  observation is enabled.
- Zero behavioural change when observation is off (no console writes, no audit events, no
  result change).
- No new dependency; reuse the existing `rich` console.
- Tail-friendly: plain incremental lines in a redirected log, not an animated bar that
  fills the log with carriage-returns.

**Non-Goals:**
- A real-time per-document feed (would bloat output and serve no one).
- Progress for the fast deterministic stages (ingest already writes per-doc audit; relate
  /select are fast enough). Only the embed loops are in scope.
- Recording progress in the audit trail. Progress is cosmetic, not an audit fact.
- Reworking `StageObserver`'s panel-after-stage model.

## Decisions

### Decision: progress via an injected callback, not via audit events

retrieve gets an optional `progress` callback parameter, default `None`. Inside the loop
it calls `progress(done, total)` at the chosen interval. `pipeline/run.py` constructs the
callback only when observation is enabled and passes it in; otherwise it passes `None` and
the loop's `if progress is not None` guard makes it a true no-op.

*Why over alternatives:*
- *Per-document audit events the observer tails live* — would add ~1000 lines to
  `audit.jsonl` per run and make progress an audit fact (it is not), violating the
  "progress is cosmetic / results identical" requirement. Rejected.
- *retrieve imports the console directly* — couples a pure pipeline stage to terminal IO
  and to the observe flag. The callback keeps retrieve ignorant of *how* progress is
  shown (console, test spy, nothing). Cleaner and unit-testable. Chosen.

### Decision: emit at a bounded interval, default ~5% steps (min every 1)

The loop computes an interval `step = max(1, total // 20)` and calls the callback when
`done % step == 0` (and once at the end). That caps updates at ~20 per stage regardless of
corpus size — readable in a `tail`, no per-document spam. The exact divisor is an
implementation detail, not a spec number.

### Decision: print plain incremental lines, not an animated rich bar

The callback prints `console.print(f"  {stage}: embedded {done}/{total}")` (dim style).
Plain lines append cleanly to a redirected log and to a TTY. A `rich.Progress` live bar
renders with carriage returns that turn a redirected log into a mess — contrary to the
tail-friendly requirement. Plain lines are the boring, auditable choice.

### Decision: callback helper lives next to StageObserver

A small factory (e.g. `StageObserver.progress_for(stage)` or a module-level
`make_progress(console, stage)`) returns the callback bound to the same console the panels
use, so progress and panels share one output stream and styling. `run.py` asks the active
observer for the callback; when observation is off there is no observer and the callback is
`None`.

## Risks / Trade-offs

- [Interval hides a stall between updates] → With ~20 updates a stall is visible within
  one interval (~5% of the corpus); acceptable, and far better than the current total
  silence. A per-document feed would remove the gap but reintroduce spam.
- [retrieve signature grows a parameter] → Keyword-only, default `None`; existing callers
  and tests are unaffected. Mirrored on `embed_chunks` for consistency.
- [Progress and the completion panel both touch the console] → Both go through the same
  observer console; ordering is natural (progress lines, then the panel). No interleaving
  risk because retrieve is synchronous.
- [Someone later asserts results differ with/without observe] → Covered by an explicit
  spec scenario and a test that runs both and diffs `audit.jsonl` + selection.
