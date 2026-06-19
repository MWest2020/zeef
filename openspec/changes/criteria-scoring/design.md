## Context

Change #1 established the deterministic spine: one canonical `Document`, rules-first
scope-filter, vector retrieval + lexical/cross-encoder rerank, three cutoff modes, an
append-only JSONL audit-trail. The relevance signal that decides the top-X is the rerank
score. It is reproducible but opaque — no written relevance definition, no per-document
rationale.

Change #2 adds graded, explainable LLM relevance without giving up the determinism and
auditability the brief requires. It introduces exactly two LLM touchpoints and a single,
explicit rule for when an LLM is allowed at all.

## Goals / Non-Goals

**Goals:**
- Make the relevance definition explicit and inspectable: articulated criteria, exported.
- Replace the opaque final score with a graded LLM relevance score *plus* a per-document
  rationale, when an LLM is available.
- Keep the middle of the pipeline (retrieve, rerank, chunking, dedup, threads, rule-based
  exclusion) deterministic, and keep `--no-llm` a fully deterministic, air-gapped run.
- Bound LLM cost explicitly (top-K pre-trim), and never cap coverage silently.

**Non-Goals (this change):**
- Categorisation / sub-topic clustering, summarisation, highlighting (the `enrich` stage).
- Using the criteria to expand or rewrite the retrieval query (retrieve still uses the raw
  refined query — keeps the deterministic middle unchanged).
- Any protocol change or new model client. Reuse `LLMProvider.complete`.

## Decisions

### D9 — The rule for "LLM or not"
An LLM is used **only** for judgement under linguistic ambiguity that has no mechanical ground
truth, and **only** where a rationale raises defensibility. Concretely in change #2: criteria
articulation and borderline relevance scoring. Everything with a mechanical ground truth —
threads (headers), duplicates (hash/cosine), rule-based exclusion, chunking, vector/lexical
retrieval, the cutoff arithmetic — stays deterministic. This rule is the design contract; new
stages must justify themselves against it.

### D10 — Criteria articulation at the begin
One LLM call maps the refined query → a small set (3–6) of named criteria
(`Criterion{label, description}`), wrapped in a `Criteria{query, items, source}` object.
`source` is `"llm"` when articulated, `"fallback"` when `--no-llm` produced a single criterion
equal to the raw query. The articulated criteria are:
- written to the audit-log with the exact prompt, model and location;
- exported as `criteria.json` (the inspectable relevance definition);
- passed to the scoring stage as the yardstick.

Parsing is deliberately boring: one criterion per line in `LABEL: beschrijving` form; lines
without a colon or empty lines are skipped; if parsing yields nothing the stage falls back to
the single raw-query criterion (and logs that it did). No JSON-mode dependency.

### D11 — LLM relevance scoring at the eind, rerank as the pre-trim
The deterministic rerank still runs and orders candidates, but it no longer decides the top-X
on its own. After rerank, the top-K candidates (K = `--score-top-k`, default 250) are scored by
the LLM against the criteria. Each scored document gets:
- `scores["llm_relevance"]` ∈ [0,1] (parsed `SCORE: 0–100`, clamped, /100);
- `scores["final"] = llm_relevance` — this is what `select` cuts on;
- `rationale` — a one-line motivation naming which criteria are hit.

Candidates **outside** the scored top-K are demoted (`final = 0.0`) with a recorded reason
("niet door LLM gescoord; buiten top-K rerank"), so scored documents are always in contention
ahead of unscored ones. The count scored vs demoted is logged — coverage is never capped
silently. `--score-top-k 0` means "score every candidate" (no demotion).

*Why rerank-as-pre-trim rather than scoring everything:* LLM scoring is the expensive step; on
~1.000 candidates scoring all is wasteful and slow. The cheap deterministic rerank narrows to a
generous K (≫ target) first. This is standard TAR funnel practice.

*Trade-off (recall):* a genuinely relevant document that the lexical rerank ranks below K never
reaches the LLM. Mitigations: K defaults well above the ~100 target; `--score-top-k 0` scores
everything when recall must be maximal; the recall-bias in `select` still applies among scored
documents. Documented here so the trade-off is a conscious choice.

### D12 — Scoring reuses `LLMProvider.complete`, temperature-0, prompt logged
No new protocol. The scoring prompt asks for a fixed two-line answer (`SCORE:` / `MOTIVATIE:`)
that is parsed with a tolerant regex; an unparseable answer scores 0 with the raw verdict kept
as the rationale (and logged), never a crash. Every score call logs its exact prompt, model and
location — same audit contract as the scope-filter LLM. `--no-llm` skips the stage entirely and
leaves `final` = rerank, so change #1 behaviour is bit-for-bit preserved.

### D13 — Two new fields, one new artifact
- `Document.rationale: str` — the per-document motivation (separate from the mechanical
  `decision_reason`, which keeps recording the cutoff arithmetic for audit).
- `criteria.json` — the articulated criteria, alongside `inventory.xlsx` / `relations.json` /
  `audit.jsonl`. `inventory.xlsx` gains a trailing `motivatie` column carrying `rationale`.

## Risks / Trade-offs

- **LLM nondeterminism** undermines reproducibility. *Mitigation:* temperature 0, full prompt +
  model + location logged, `--no-llm` for a fully deterministic run; the criteria + every score
  are reconstructable from the log.
- **Recall funnel** (D11). *Mitigation:* generous default K, `--score-top-k 0` escape hatch,
  recall-bias still applies; trade-off documented and logged.
- **Prompt-format drift** (model ignores the two-line format). *Mitigation:* tolerant parsing,
  score-0 fallback with the raw answer retained, never a crash.
- **Cost** on large sets. *Mitigation:* K-bounded by default and reported; cloud usage already
  logged via `llm_usage_log`.

## Migration Plan

Additive — no migration. `--no-llm` runs are unchanged. Existing run directories are unaffected;
new runs simply gain `criteria.json` and a `motivatie` column. Rollback is trivial (no state).

## Open Questions

- Default `--score-top-k`: 250 is a guess sized to a ~100 target; revisit against the real
  dataset's candidate count on the day.
- Should the criteria also expand the retrieval query (better recall, but the deterministic
  middle changes)? Deferred to a follow-up; out of scope here.
