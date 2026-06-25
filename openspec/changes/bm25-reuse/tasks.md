## 1. Dependency (supply-chain procedure)

- [ ] 1.1 Verify the `rank_bm25` version to be pinned has a PyPI release date older than the
      7-day cooldown window (defang same-week supply-chain attacks); record the version + date
- [ ] 1.2 Add `rank_bm25` to `pyproject.toml` runtime dependencies with a comment (pure Python,
      sovereign/air-gapped, BM25 reuse — see design D-FOOTPRINT)
- [ ] 1.3 Resolve the lockfile with `uv lock`; review the `uv.lock` diff (resolved URL, hashes,
      no unexpected transitive deps) and confirm no lifecycle/build scripts
- [ ] 1.4 `uv sync` into the venv; confirm `import rank_bm25` works offline

## 2. Swap the implementation (`drivers/local.py`)

- [ ] 2.1 In `LexicalReranker.rerank`, keep the `if not docs: return []` guard (empty corpus)
- [ ] 2.2 Tokenise with `zeef.similarity.tokenize`: `corpus = [tokenize(d) for d in docs]`
- [ ] 2.3 Build `BM25Okapi(corpus, k1=self.k1, b=self.b, epsilon=0.25)` — epsilon passed
      **explicitly** (D-EPSILON)
- [ ] 2.4 Score with the **deduplicated** query: `get_scores(sorted(set(tokenize(query))))`
      (D-DEDUP)
- [ ] 2.5 Return `_normalize_scores(list(scores))` — wrapper unchanged, 0..1 enforced in one place
- [ ] 2.6 Leave class name, `name`/`location`, constructor (`k1=1.5, b=0.75`), `_normalize_scores`
      and `HashingEmbed` untouched

## 3. Adversarial equivalence test (`tests/test_retrieve_rerank.py`)

- [ ] 3.1 Repeated-term query: deduped feed yields the same ordering as the single-term query
      (D-TEST case 1)
- [ ] 3.2 High-document-frequency query term (>50% of candidates): assert the new ordering is
      defensible — a doc also carrying a rare discriminating term ranks above one with only the
      common term (D-TEST case 2)
- [ ] 3.3 Keep the existing regression: query `"beta gamma"` → `d2` ranks above `d1`
- [ ] 3.4 Assert output invariants on every case: length == len(docs), all values in 0.0..1.0,
      empty docs → `[]`

## 4. Verify (isolated — change 1 only)

- [ ] 4.1 `uv run pytest` — full suite green (offline)
- [ ] 4.2 `uv run ruff check` clean on touched files
- [ ] 4.3 Run the sovereign smoke-run end to end: `ZEEF_SMOKE=1 uv run pytest
      tests/test_sovereign_smoke.py -s` (with Ollama up) — confirm a full sovereign run is green
      with the swapped reranker
- [ ] 4.4 `openspec validate bm25-reuse`
- [ ] 4.5 Update `CHANGELOG.md` (dated entry: what swapped, raw-score shift noted, files, tests)
