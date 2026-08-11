## 1. Project scaffold

- [x] 1.1 Initialize `uv` project (`pyproject.toml`, Python 3.12+), add core deps (pydantic v2, typer, rich, openpyxl)
- [x] 1.2 Create package layout: `src/zeef/` with `models.py`, `protocols.py`, `config.py`, `audit.py`, `cli.py`, `pipeline/`, `drivers/`, `loaders/`
- [x] 1.3 Add dev tooling (ruff, pytest) and a `tests/` skeleton with fixtures dir
- [x] 1.4 Enforce the ≤200-line-per-file rule (lint check or CI guard)

## 2. Canonical data model

- [x] 2.1 Implement `Chunk`, `Relation`, `Document` pydantic v2 models in `models.py`
- [x] 2.2 Implement content-addressed stable id (sha256 of normalized text + source path) — extracted to dependency-free `zeef/ids.py` (cross-repo `doc_id` contract)
- [x] 2.3 Unit tests: reproducible id across runs; relations carry evidence

## 3. Protocols and profiles

- [x] 3.1 Define `Loader`, `EmbeddingProvider`, `RerankerProvider`, `LLMProvider` Protocols in `protocols.py`
- [x] 3.2 Implement `Profile` settings mapping `--profile` to a provider triple (`profiles.resolve_providers` → `ProviderBundle`); `NullLLM` for `--no-llm`
- [x] 3.3 Implement sovereign drivers — air-gapped default is deterministic local (`HashingEmbed` + `LexicalReranker`, no network/weights); Ollama embedding + LLM behind the same interface, host-gated (see report: deviation from the cross-encoder wording, chosen so the acceptance run is genuinely air-gapped)
- [x] 3.4 Implement cloud drivers (Claude API LLM + Voyage hosted embedding/reranker), keys from env; construction allowed without keys, real calls gated on the key (not live-tested)
- [x] 3.5 Tests: profile switch resolves different providers with no pipeline code change

## 4. Audit-trail

- [x] 4.1 Implement append-only JSONL audit writer in `audit.py` (timestamp, stage, doc ids, action, inputs)
- [x] 4.2 Record model id + execution location (`local`/`cloud`) and exact prompt for LLM events
- [x] 4.3 Tests: every stage emits events; a decision is reconstructable from the log alone

## 5. Ingest & normalize

- [x] 5.1 Implement loader registry and selection (`can_load` / `load`)
- [x] 5.2 `.eml`/`.msg` loader preserving threading headers; attachments as `attachment-of` documents
- [x] 5.3 Digital PDF loader; tag text-less PDFs as `pdf_scanned` (no OCR this change)
- [x] 5.4 Text normalization and metadata extraction into `Document`
- [x] 5.5 Tests: headers retained; unsupported files skipped with audit event; scanned PDF flagged

## 6. Relate

- [x] 6.1 Thread reconstruction from `Message-ID`/`In-Reply-To`/`References`; heuristic fallback marked as such
- [x] 6.2 Exact-duplicate detection via content hash; near-duplicate via MinHash + embedding cosine
- [x] 6.3 Tests: 5-mail thread → one cluster; identical docs → `duplicate-of`, counted once

## 7. Scope-filter

- [x] 7.1 Ordered deterministic rule set (forwarded-only, calendar invite, process notification, thread-tail, duplicate)
- [x] 7.2 LLM fallback for undecided residue only; skipped under `--no-llm`
- [x] 7.3 Every exclusion writes `decision_reason` + audit event (LLM events include the prompt)
- [x] 7.4 Tests: rule excludes without LLM call; `--no-llm` leaves residue undecided

## 8. Embed, retrieve, rerank

- [x] 8.1 Deterministic chunking; embed chunks via `EmbeddingProvider`
- [x] 8.2 First-pass retrieval vs. refined query (vector, optional BM25 hybrid); record `embed_sim`
- [x] 8.3 Rerank candidates via `RerankerProvider`; record `rerank` and compute `final` score
- [x] 8.4 Tests: candidates carry scores; rerank reorders

## 9. Select

- [x] 9.1 Implement `--top-n`, `--threshold`, `--target` (adaptive, reports score knee)
- [x] 9.2 Configurable recall bias on ties / near-threshold, logged
- [x] 9.3 Set `decision = selected` + `decision_reason`; duplicates/thread-tails are already `out_of_scope`, so they occupy no slot
- [x] 9.4 Tests: each mode reproducible; near-threshold doc included under recall bias

## 10. Export

- [x] 10.1 `inventory.xlsx` (id, score, category, summary, reason); empty summary under `--no-llm`
- [x] 10.2 `relations.json` graph export
- [x] 10.3 `audit.jsonl` lives in the run output directory (stages write straight to `<out>/audit.jsonl`)
- [x] 10.4 Tests: all three artifacts present; inventory columns correct

## 11. CLI wiring

- [x] 11.1 `zeef converge` Typer command threading the pipeline; one run directory per invocation
- [x] 11.2 Flag validation (mutually exclusive cutoff modes; profile; `--no-llm`)
- [x] 11.3 `rich` progress + final summary, separate from the audit-trail
- [x] 11.4 End-to-end test: `sovereign --no-llm` on mixed `.eml`/PDF fixtures with no network

## 12. Acceptance & docs

- [x] 12.1 Verify all change #1 acceptance criteria pass against fixtures (e2e: 3 artifacts, thread→1 unit, exact dup→1 slot, every exclusion reasoned, no network)
- [x] 12.2 Update README + docs site with the converge usage and outputs
- [x] 12.3 Update CHANGELOG with the change
