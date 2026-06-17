## 1. Project scaffold

- [ ] 1.1 Initialize `uv` project (`pyproject.toml`, Python 3.12+), add core deps (pydantic v2, typer, rich, openpyxl)
- [ ] 1.2 Create package layout: `src/zeef/` with `models.py`, `protocols.py`, `config.py`, `audit.py`, `cli.py`, `pipeline/`, `drivers/`, `loaders/`
- [ ] 1.3 Add dev tooling (ruff, pytest) and a `tests/` skeleton with fixtures dir
- [ ] 1.4 Enforce the ≤200-line-per-file rule (lint check or CI guard)

## 2. Canonical data model

- [ ] 2.1 Implement `Chunk`, `Relation`, `Document` pydantic v2 models in `models.py`
- [ ] 2.2 Implement content-addressed stable id (sha256 of normalized text + source path)
- [ ] 2.3 Unit tests: reproducible id across runs; relations carry evidence

## 3. Protocols and profiles

- [ ] 3.1 Define `Loader`, `EmbeddingProvider`, `RerankerProvider`, `LLMProvider` Protocols in `protocols.py`
- [ ] 3.2 Implement `Profile` settings mapping `--profile` to a provider triple; `NullLLM` for `--no-llm`
- [ ] 3.3 Implement sovereign drivers (Ollama/vLLM embedding + cross-encoder reranker + LLM)
- [ ] 3.4 Implement cloud drivers (Claude API LLM + hosted embedding/reranker), keys from env/SOPS
- [ ] 3.5 Tests: profile switch resolves different providers with no pipeline code change

## 4. Audit-trail

- [ ] 4.1 Implement append-only JSONL audit writer in `audit.py` (timestamp, stage, doc ids, action, inputs)
- [ ] 4.2 Record model id + execution location (`local`/`cloud`) and exact prompt for LLM events
- [ ] 4.3 Tests: every stage emits events; a decision is reconstructable from the log alone

## 5. Ingest & normalize

- [ ] 5.1 Implement loader registry and selection (`can_load` / `load`)
- [ ] 5.2 `.eml`/`.msg` loader preserving threading headers; attachments as `attachment-of` documents
- [ ] 5.3 Digital PDF loader; tag text-less PDFs as `pdf_scanned` (no OCR this change)
- [ ] 5.4 Text normalization and metadata extraction into `Document`
- [ ] 5.5 Tests: headers retained; unsupported files skipped with audit event; scanned PDF flagged

## 6. Relate

- [ ] 6.1 Thread reconstruction from `Message-ID`/`In-Reply-To`/`References`; heuristic fallback marked as such
- [ ] 6.2 Exact-duplicate detection via id; near-duplicate via MinHash/SimHash + embedding cosine
- [ ] 6.3 Tests: 5-mail thread → one cluster; identical docs → `duplicate-of`, counted once

## 7. Scope-filter

- [ ] 7.1 Ordered deterministic rule set (forwarded-only, calendar invite, process notification, thread-tail, duplicate)
- [ ] 7.2 LLM fallback for undecided residue only; skipped under `--no-llm`
- [ ] 7.3 Every exclusion writes `decision_reason` + audit event (LLM events include the prompt)
- [ ] 7.4 Tests: rule excludes without LLM call; `--no-llm` leaves residue undecided

## 8. Embed, retrieve, rerank

- [ ] 8.1 Deterministic chunking; embed chunks via `EmbeddingProvider`
- [ ] 8.2 First-pass retrieval vs. refined query (vector, optional BM25 hybrid); record `embed_sim`
- [ ] 8.3 Rerank candidates via `RerankerProvider`; record `rerank` and compute `final` score
- [ ] 8.4 Tests: candidates carry scores; rerank reorders

## 9. Select

- [ ] 9.1 Implement `--top-n`, `--threshold`, `--target` (adaptive, reports score knee)
- [ ] 9.2 Configurable recall bias on ties / near-threshold, logged
- [ ] 9.3 Set `decision = selected` + `decision_reason`; ensure duplicates occupy one slot
- [ ] 9.4 Tests: each mode reproducible; near-threshold doc included under recall bias

## 10. Export

- [ ] 10.1 `inventory.xlsx` (id, score, category, summary, reason); empty summary under `--no-llm`
- [ ] 10.2 `relations.json` graph export
- [ ] 10.3 Copy `audit.jsonl` into the run output directory
- [ ] 10.4 Tests: all three artifacts present; inventory columns correct

## 11. CLI wiring

- [ ] 11.1 `zeef converge` Typer command threading the pipeline; one run directory per invocation
- [ ] 11.2 Flag validation (mutually exclusive cutoff modes; profile; `--no-llm`)
- [ ] 11.3 `rich` progress + final summary, separate from the audit-trail
- [ ] 11.4 End-to-end test: `sovereign --no-llm` on mixed `.eml`/PDF fixtures with no network

## 12. Acceptance & docs

- [ ] 12.1 Verify all change #1 acceptance criteria pass against fixtures
- [ ] 12.2 Update README + docs site with the converge usage and outputs
- [ ] 12.3 Update CHANGELOG with the change
