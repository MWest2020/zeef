## Why

The criteria require the result to be inspectable — **both the selected ~100 and the rest** — and
the sub-topics to be presentable to the requester as a choice menu. For a government worker without
training, a raw `inventory.xlsx` plus loose JSON files is not a menu. A single, self-contained HTML
file that renders the run artifacts makes this tangible, and is at the same time the visible
auditability demo where Woo wants to see the difference from classic tooling.

To show "the rest", the export must also write the full excluded set with reasons in a
machine-readable form — the follow-up deferred from earlier changes lands here.

## What Changes

- **NEW** A self-contained, offline, single-file HTML report (`report.html`): system fonts, vanilla
  JS, no CDN / no external fonts / no external scripts / no `fetch`, EUPL-1.2 header, in the fixed
  explainer style. Read-only. The run data is injected **inline** as JSON in a
  `<script type="application/json">` block so the file opens via `file://` without a server or
  network (air-gapped-safe).
- **NEW**/**MODIFIED** Export writes the full **excluded set** with reasons (`excluded.json`,
  machine-readable), distinguishing validity exclusions (`validity:*`) from semantic out-of-scope,
  and generates `report.html` with the run data embedded inline.
- The viewer shows: the selected core grouped by onderwerp/deelonderwerp as a collapsible menu (from
  `topics.json`); per document its score, motivation (rationale), summary (when present), selection
  reason, redaction status (from the canonical `redaction_note` metadata, not `decision_reason`),
  and its relations (attachments / threads / duplicates / `overlaps-with`); and the full excluded
  set grouped by reason.

## Capabilities

### New Capabilities
- `viewer-ui`: a self-contained, offline, single-file HTML report rendering the selected core as a
  navigable onderwerp/deelonderwerp menu, the full excluded set grouped by reason, and per-document
  motivation / summary / reason / redaction status / relations — with all untrusted text escaped.

### Modified Capabilities
- `export`: writes the full excluded set with reasons (`excluded.json`) and generates `report.html`
  with the run data embedded inline.

## Impact

- **Affected specs**: new `viewer-ui`; modified `export`.
- **Affected code**: new `src/zeef/templates/report.html` (the single-file template); `export.py`
  (`build_report_data`, `write_report_html`, `write_excluded`); `pipeline/run.py` (generate
  `report.html` + `excluded.json` in the export stage; add both to the audit artifact list — all
  additive). No pipeline logic changes.
- **No new dependencies, no CDN, no network**: the viewer is vanilla JS over inline JSON; it opens
  via `file://`. Fits the air-gapped / sovereign default.
- **Security**: all untrusted text (LLM summaries and topic labels, document titles) is HTML-escaped
  at render time; the inline JSON is `<`/`>`-escaped so document content cannot break out of the
  `<script>` block. Only presentation fields are inlined — not full document text (size + exposure).
- **Determinism / sovereignty**: pure presentation over existing artifacts; changes no selection or
  scoring behaviour, and recomputes nothing in JS (the viewer can never diverge from the run).
- **Out of scope (follow-up)**: highlighting hits inside source documents; OpenAnonymiser
  integration; a live server/back-end.
