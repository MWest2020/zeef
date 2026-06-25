## 0. Verify before implementing (gates everything below)

- [ ] 0.1 Read the current Voyage **embeddings** docs for `voyage-3`: per-input token cap,
      per-request input-count limit, per-request total-token budget. Record the actual numbers.
- [ ] 0.2 Read the current Voyage **rerank** docs for `rerank-2`: per-document/context limit,
      per-request document-count limit, total-token budget. Record the actual numbers.
- [ ] 0.3 **Resolve D-RERANK-SPLIT**: confirm from the rerank docs whether the relevance score is
      an absolute per-(query, document) value independent of the other documents in the request.
      Record the answer and, if NO, switch the rerank tasks (section 3) to the truncation-only
      fallback before writing any code.
- [ ] 0.4 Reconcile the provisional defaults in design D-LIMITS with the verified numbers; pin the
      final defaults (and note any that differ from the proposal).

## 1. Config (`config.py`)

- [ ] 1.1 Add `voyage_embed_chars`, `voyage_rerank_chars`, `voyage_batch_size`,
      `voyage_batch_chars` to `Settings` (env prefix `ZEEF_`), each with the verified default and a
      one-line comment citing the Voyage limit it bounds
- [ ] 1.2 Defaults conservative; values are operational knobs, not secrets

## 2. Embedder truncation + batching (`drivers/cloud.py`)

- [ ] 2.1 In `VoyageEmbed.embed`, truncate each input to `voyage_embed_chars` before sending
- [ ] 2.2 Split inputs into batches bounded by **both** `voyage_batch_size` (count) and
      `voyage_batch_chars` (cumulative chars); post sequentially
- [ ] 2.3 Concatenate the returned vectors in **original input order**; assert
      `len(output) == len(input)`
- [ ] 2.4 Surface a truncation counter (inputs truncated, max original length) for the audit event

## 3. Reranker — branches on D-RERANK-SPLIT (task 0.3)

**If score independence is CONFIRMED:**
- [ ] 3.1a Truncate each document to `voyage_rerank_chars`
- [ ] 3.2a Split documents into batches bounded by count + cumulative chars; post sequentially
- [ ] 3.3a Reassemble per-document scores in **original index order**; assert length preserved

**If score is BATCH-RELATIVE (cannot split):**
- [ ] 3.1b Truncate each document with `voyage_rerank_chars` so the full candidate set fits one
      request
- [ ] 3.2b If it still cannot fit the single-request budget, **fail loudly** with a clear message
      (do not silently split — that would change results)

## 4. Auditability

- [ ] 4.1 Emit a `truncation` audit event when truncation fires (endpoint, count truncated, max
      original length) — never silent
- [ ] 4.2 Record the four applied limits in `run-manifest.json` `params` (`run.py:177-189`)

## 5. Tests (`tests/`)

- [ ] 5.1 Fake `_post` that records each batch's payload; assert no batch exceeds `voyage_batch_size`
      or `voyage_batch_chars`
- [ ] 5.2 Embedder: output vector order matches input order across multiple batches; length preserved
- [ ] 5.3 Per-input truncation applied (oversized input is shortened, not rejected); truncation
      counter reflects it
- [ ] 5.4 Reranker (per the resolved branch): confirmed-path reassembles scores in original index
      order across batches; fallback-path fails loudly when a single request cannot fit
- [ ] 5.5 Selection-semantics no-op: a small in-memory corpus run produces the same selection
      whether or not batching splits (batch size 1 vs large), proving the contract is unchanged

## 6. Verify

- [ ] 6.1 `uv run pytest` — full suite green
- [ ] 6.2 `uv run ruff check` clean on touched files
- [ ] 6.3 `openspec validate voyage-transport-hardening`
- [ ] 6.4 (Optional, key-gated) a real cloud converge run over the blind corpus completes without
      a Voyage HTTP error — only after 0.x verification and explicit go-ahead
- [ ] 6.5 Update `CHANGELOG.md` (dated entry: drivers hardened, limits recorded, files, tests)
