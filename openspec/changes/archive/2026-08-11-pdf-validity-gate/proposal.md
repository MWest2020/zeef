## Why

The exploration runs on a **PDF-only** dataset delivered by secure transfer; every document
is OCR-compatible. Two consequences the current pipeline does not cover:

- The email-shaped exclusion machinery (forwarded-only, no-reply, receipt confirmation, thread
  heuristics) **does not fire** on an all-PDF set. "Exclude with a reason" then leans almost
  entirely on dedup and semantic scope — there is no protection against *mechanically unusable*
  documents (failed OCR, corrupt/unreadable PDF, effectively empty text) reaching the relevance
  phase.
- A corrupt or empty document in the top-100 is worse than a slightly weaker selection: it is
  visible noise that a reviewer immediately distrusts. We want a deterministic floor that removes
  demonstrable junk **before** scoring, every removal carrying an explicit reason.

There is a trap: some documents are **redacted** and therefore legitimately contain little text.
A naive empty-text threshold would exclude a heavily-redacted-but-relevant document as "empty" —
a false exclusion that costs recall and looks bad live. The gate must distinguish *unusable* from
*redacted*.

This is explicitly a **validity** gate, not a relevance filter. It removes documents that cannot
be assessed at all; it does not raise the relevance bar. Relevance recall is unchanged.

## What Changes

A new deterministic pre-flight stage runs after ingest and before scope-filter/retrieve. It
classifies *usability* (not relevance) per document and excludes the unusable with a
machine-readable reason, while keeping redacted-but-readable documents in the race.

- **NEW** Validity-gate stage: per document deterministic checks on (a) parse success,
  (b) extractable-text volume above a minimum, (c) language-detectability (a soft signal, never
  a hard exclusion on its own). A failed hard check → `out_of_scope` with a specific
  `decision_reason` (`validity:corrupt-pdf`, `validity:empty-after-ocr`). All logged. No LLM.
- **NEW** Redaction-aware: text below the empty threshold **but** with redaction signal (high
  share of black-box glyphs / repeated `[gelakt]` / Woo-exception annotations such as `5.1.2e`)
  → document **kept** and flagged `verminderd leesbaar (vermoedelijk gelakt)`. A natural bridge
  to OpenAnonymiser in the presentation.
- **MODIFIED** `ingest`: each `Document` records extraction-health metadata (`char_count`,
  `parse_ok`, `redaction_ratio`) so the gate decides deterministically without re-reading the
  file.
- **MODIFIED** counts/reporting: validity exclusions are a separate, reportable category, distinct
  from semantic out-of-scope.

Out of scope here (already deterministic elsewhere): exact/near-duplicate exclusion stays in
relate + scope-filter (`rule_duplicate`); the gate does not duplicate that path.

## Impact

- **Specs**: new `validity-gate`; modified `ingest`.
- **Code**: `loaders/pdf_loader.py` (health metadata, soft parse failure), `loaders/email_loader.py`
  (health metadata for uniformity), new `health.py`, new `pipeline/validity.py`,
  `pipeline/run.py` (stage between ingest and relate; manifest params; validity count),
  `cli.py` (`--min-chars`/`--redaction-ratio`, validity count in summary), `config.py`
  (`validity_min_chars`, `redaction_ratio_threshold`). `models.py` is **not** touched — health
  lives in the existing `metadata` dict.
- **No new mandatory runtime deps**: counting + the redaction heuristic is pure Python over
  already-extracted text. Language detection is optional; its absence → "language unknown" (soft),
  never a crash.
- **Determinism/sovereignty**: the gate is fully deterministic, no LLM; identical under `--no-llm`
  and air-gapped.
