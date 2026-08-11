## Context

Changes #1–#3 are merged: the run produces `inventory.xlsx`, `relations.json`, `criteria.json`,
`topics.json`, `run-manifest.json` and `audit.jsonl`. What is missing is a human-facing,
inspectable view that a government worker can open without training — and that doubles as the
sovereignty/auditability demo. This change adds that as a read-only, single-file HTML report plus
the excluded-set export it needs.

## Goals / Non-Goals

**Goals**
- One self-contained `report.html` that opens offline (`file://`) and issues zero external requests.
- Show both the selected core (as an onderwerp/deelonderwerp menu) and the full excluded set with
  reasons.
- Be presentation-only: render existing artifacts, never recompute the selection.

**Non-Goals**
- A server or any back-end; live search over thousands of rows.
- Highlighting inside source documents; rendering full document text.
- Changing any pipeline behaviour.

## Decisions

### U1 — Single file, inline data, no network
The cleanest way to satisfy "self-contained, no CDN, air-gapped" is to use no `fetch`: the export
step injects the run data as a JSON blob into a static HTML template and writes `report.html`. It
opens on double-click (`file://`), offline. The template uses system fonts and vanilla JS only — no
framework, no build step.

### U2 — Read-only, presentation-only
The viewer changes nothing; it renders. All truth comes from the artifacts (`topics.json`,
inventory data, the excluded set, relations, manifest). No recomputation in JS → the UI can never
silently diverge from the run.

### U3 — "Both the 100 and the rest"
Alongside the core, the viewer shows the excluded set grouped by reason (validity vs semantic), so
the controllability requirement is met literally. This requires export to write the excluded
documents + reasons (`excluded.json`) — the follow-up deferred from earlier changes.

### U4 — The menu is the onderwerp/deelonderwerp tree
`topics.json` is the navigation: collapsible onderwerpen → deelonderwerpen → document list; opening
a document shows its score / rationale / summary / reason / redaction status / relations.

### U5 — Escaping and inline-injection safety (the security spine)
The report shows untrusted text — LLM summaries and topic labels, document titles — to a ministry.
Two layers: (a) the inline JSON has `<`/`>`/`&` escaped (`<…`) so a document field containing
`</script>` cannot break out of the `<script type="application/json">` block; (b) at render time the
JS writes every untrusted string via the DOM text path (`textContent`) / an explicit escape, so a
`<script>` payload is shown as text, never executed. Escaping happens at render, not only at
injection.

### U6 — Redaction status from the canonical metadata key
A redacted-but-kept document's "vermoedelijk gelakt" status lives in `metadata["redaction_note"]`
(`REDACTION_META_KEY`), not in `decision_reason` — the latter is overwritten by select/scope-filter
(change #1's handoff). The viewer reads the canonical key and shows the reduced-readability badge.

### U7 — Inline only presentation fields
To keep the file small, only presentation fields are inlined (id, name, score, labels, reason,
summary, rationale, redaction status, relations) — never the full document text. Source is referred
to by `source_path`/id.

## Risks / Trade-offs

- **File size on large runs.** Inline JSON grows with the core. Mitigation: only presentation fields
  (no document text); the core is ~100, the excluded set is summarised per reason.
- **Static test of "no network".** A pytest cannot open a browser. Mitigation: assert statically
  that the generated HTML contains no external URLs, no `fetch`/`XMLHttpRequest`, no external
  `<script src>`/`<link>` — the verifiable equivalent of "zero external requests".
- **Single file = no shared assets.** Deliberate: portability and offline openability outweigh asset
  reuse for a demo artifact.

## Migration Plan

Additive. The report and excluded-set are written in the existing export stage; no pipeline logic
changes, no artifact removed. Under `--no-llm` the report still renders (summaries simply absent).
