## 1. Excluded-set export

- [x] 1.1 `export.py`: `write_excluded(docs, path)` → `excluded.json` — per out-of-scope document id, name, doc_type, reason, reason-category (`validity` if `decision_reason` starts with `validity:`, else `semantic`), redaction status
- [x] 1.2 Test the shape (validity vs semantic distinguishable)

## 2. HTML template (single file, no network)

- [x] 2.1 `src/zeef/templates/report.html` — single-file template: EUPL-1.2 header, system fonts, vanilla JS, **no** CDN / external fonts / external scripts / `fetch`
- [x] 2.2 A `<script type="application/json">` data block; JS reads + `JSON.parse`es it, renders the DOM
- [x] 2.3 Collapsible onderwerp/deelonderwerp menu from `topics`; per-document detail: score, rationale, summary, reason, redaction badge, relations (clickable)
- [x] 2.4 Excluded set grouped per reason (validity vs semantic)
- [x] 2.5 Render every untrusted string via the DOM text path / explicit escape (no `innerHTML` of untrusted data)

## 3. Report generation (export)

- [x] 3.1 `export.py`: `build_report_data(query, generated_at, selected, topics, all_docs)` → presentation-only dict (no document text); reads redaction status from `REDACTION_META_KEY`
- [x] 3.2 `export.py`: `write_report_html(data, path)` — inject the JSON into the template with `<`/`>`/`&` escaped (no `</script>` break-out), write `report.html`

## 4. Wiring (additive)

- [x] 4.1 `run.py`: in the export stage, write `excluded.json` and `report.html`; add both to the export audit artifact list

## 5. Tests

- [x] 5.1 Offline / no external requests: the generated `report.html` contains no external URL, no `fetch`/`XMLHttpRequest`, no external `<script src>`/`<link>` (the verifiable equivalent of zero requests)
- [x] 5.2 Escaping: a label/summary/title with a `<script>` payload appears only escaped in the output, not as a live tag (assert on the generated output)
- [x] 5.3 Excluded set grouped per reason, validity distinguished from semantic
- [x] 5.4 A redacted document shows the redaction status from `REDACTION_META_KEY`
- [x] 5.5 `openspec validate viewer-ui --strict`
- [x] 5.6 `uv run pytest` with **and** without `--extra cloud` (without still collects cleanly — keep change #3's win); `ruff` clean; ≤200-line check (the `.html` template is exempt)

## 6. Docs & changelog

- [x] 6.1 README + de-pijplijn: `report.html` + `excluded.json` as run outputs; the offline single-file viewer
- [x] 6.2 `CHANGELOG.md`: dated entry
