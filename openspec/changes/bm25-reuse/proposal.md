## Why

The sovereign lexical reranker in `src/zeef/drivers/local.py` (`LexicalReranker`) carries a
hand-written Okapi-BM25 implementation. It works and is deterministic, but it is bespoke code
on the relevance path: every BM25 edge case (idf sign, length normalisation, division-by-zero
on empty corpora) is ours to get right and ours to maintain. "Boring and auditable" argues for
reusing a well-understood, battle-tested library instead of carrying our own scoring maths.

`rank_bm25` is the obvious reuse: pure Python, no network, no model weights — it stays inside
the air-gapped sovereign profile. The original argument for hand-rolling BM25 was to avoid a
dependency footprint that "might not make the day". That argument no longer holds (see
design.md, D-FOOTPRINT): `datasketch` and `scipy` are already first-class dependencies and the
`relate` MinHash stage pulls `numpy` into every sovereign run. `rank_bm25` adds nothing heavy on
top of a runtime path that already carries `numpy`. The footprint case for self-build has
lapsed; reuse is the lower-risk option.

## What Changes

- **MODIFIED** `LexicalReranker.rerank` swaps the hand-written BM25 loop for `rank_bm25.BM25Okapi`.
  The class name, constructor signature (`k1=1.5, b=0.75`), `name`/`location` attributes and the
  `_normalize_scores` 0..1 wrapper all stay exactly as they are. Tokenisation stays
  `zeef.similarity.tokenize` — we feed pre-tokenised lists to `rank_bm25` so tokenisation is
  identical to the rest of the pipeline.
- **MODIFIED** Query terms are fed **deduplicated** (`sorted(set(tokenize(query)))`). The current
  code computes `q_terms = set(...)` so every query term counts once; `rank_bm25.get_scores`
  iterates the query list *without* dedup, so a repeated query term would double-count and
  silently change ordering. Dedup is an explicit equivalence requirement, not an implementation
  detail (design.md, D-DEDUP).
- **MODIFIED** The `BM25Okapi` `epsilon` (negative-idf floor) is fixed explicitly rather than
  left implicit, so the "scores stay ≥ 0" invariant that protects `_normalize_scores` is pinned
  in code and in the spec (design.md, D-EPSILON).
- **NEW** dependency: `rank_bm25` (pure Python, air-gapped). Added under the supply-chain
  procedure: release-age cooldown check, `uv.lock` diff review, no lifecycle scripts.

## Capabilities

### Modified Capabilities
- `retrieve-rerank`: the sovereign lexical reranker is now backed by a vendored, well-understood
  BM25 library. Its observable contract (signature, length/order, strict 0..1 normalisation,
  determinism, air-gapped) is unchanged; ordering equivalence to the previous implementation is a
  pinned, adversarially tested requirement.

## Impact

- **Affected specs**: modified `retrieve-rerank` (sovereign lexical reranker scoring contract).
- **Affected code**: `src/zeef/drivers/local.py` (`LexicalReranker.rerank` body only;
  `_normalize_scores` and `HashingEmbed` untouched). `pyproject.toml` + `uv.lock` (add
  `rank_bm25`).
- **Callers — unchanged**: `profiles.py:51,53` (only constructs `LexicalReranker()`),
  `pipeline/retrieve.py:65` (`_hybrid` calls `.rerank`), `pipeline/rerank.py` (via the
  `RerankerProvider` interface). None see a contract change.
- **Tests touched**: `tests/test_retrieve_rerank.py` (the `rerank` reordering regression assert
  must still hold; a new equivalence vector is added). `test_profiles.py` (isinstance +
  `RerankerProvider` protocol — unaffected). `test_score/criteria/summarise/topics` only construct
  `LexicalReranker()` for the bundle — unaffected by the internal swap.
- **Determinism / sovereignty preserved**: pure Python, no network, no weights; same input → same
  output. `numpy` is already on every sovereign run via `relate`/MinHash, so no new runtime weight.
- **Merge-safety**: this change touches `drivers/local.py`, `pyproject.toml`, `uv.lock` and
  `test_retrieve_rerank.py` only — fully disjoint from `structured-llm-score`. The sole shared
  file across the two changes is `CHANGELOG.md` (append-only, trivial textual merge).
- **Out of scope**: the `relate`/MinHash path, the cloud `VoyageReranker`, the `_hybrid` blending
  weights, and the selection philosophy (whether rerank drives selection — that is
  `converge-ranking`'s concern).
