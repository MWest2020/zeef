## Context

All-PDF, OCR-compatible, delivered offline. The pipeline already has deterministic dedup,
deterministic scope rules (mostly email-shaped) and an LLM scope-filter for edge cases. What is
missing is a guard against documents that *cannot be assessed at all*. This change adds that guard
as its own stage and keeps it strictly mechanical.

## Decisions

- **V1 — Validity ≠ relevance.** The gate answers "can this document be assessed?", never "is it
  relevant?". It runs before retrieve/score and only removes unusable docs. Validity exclusions are
  a separate category in counts/audit (`validity:*` reason prefix), distinct from semantic
  out-of-scope. It reuses `decision = out_of_scope`, but makes the *reason* machine-distinguishable.

- **V2 — Deterministic checks only, cheap-first.** Order: `parse_ok` (corrupt) → empty-after-OCR
  (`char_count < min_chars`, redaction-aware) → language-undetectable (soft). First hard match
  wins, with a human-readable reason. No LLM, reproducible.
  Exact/near-duplicate exclusion is **not** part of the gate: it is already handled deterministically
  and audited in relate (`duplicate-of` relations) + scope-filter (`rule_duplicate`). Duplicating it
  in the gate would create two code paths excluding duplicates with different reason strings — the
  gate consumes nothing from dedup and leaves that responsibility where it already works.

- **V3 — Redaction-aware empty handling (the live trap).** A document below the threshold is not
  automatically excluded as empty. `redaction_ratio` is computed at ingest: the share of redaction
  signal in the extraction — black-box glyphs, repeated `[gelakt]`/`[…]`, Woo annotations
  (`5.1.(1|2|5)`, `10.(1|2)`, `11.1`). Above `redaction_ratio_threshold` → **kept**, flagged, stays
  `undecided`. Only genuinely empty, low-redaction docs → `empty-after-ocr`. Thresholds live in
  `config.py`, are recorded in the manifest, and are deliberately conservative (prefer keeping over
  false exclusion).

- **V4 — Health metadata once, at ingest.** The loaders set `char_count`, `parse_ok`,
  `redaction_ratio` on `Document.metadata`. The gate reads those; it never re-opens the file. This
  keeps the gate a pure function and the per-stage timing honest. A document that lacks the metadata
  (a loader that does not set it) defaults to usable, so the gate never falsely excludes.

- **V5 — Nothing is silent.** Every decision → an audit event (id, check, reason). The CLI summary
  reports the validity count separately. The audit-log already makes "the rest" reconstructable.

## Risks / tradeoffs

- **Threshold tuning under time pressure.** `min_chars`/`redaction_ratio_threshold` are guesses
  until the real set is seen. Mitigation: conservative defaults (toward keeping), both logged in the
  manifest → reproducible and auditable, and exposed as CLI flags.
- **Redaction-heuristic false negatives.** An unexpected redaction style reads as empty. Mitigation:
  additive (every recognised signal counts) + a specific reason → misclassification is visible in
  the audit.
- **Language-detection scope-creep.** Soft signal only; never any hard exclusion → no valid Dutch
  document with thin text is dropped. The detector is optional; its absence is logged as "unknown".
