## Research finding (2026-06-26) — D-EPSILON is wrong; proposal left OPEN, do not apply as specced

A pre-implementation review against the actual `rank_bm25==0.2.2` source and empirical edge-case
tests found that this change is **not** the behavioural no-op the design claims. Recorded here so a
future reader does not implement it on the false premise.

- **D-EPSILON's core invariant is false.** The design states the epsilon floor keeps all score
  contributions non-negative, so `_normalize_scores` "cannot emit a negative value." It can.
  `BM25Okapi` floors a negative idf to `eps = epsilon * average_idf`, but `average_idf` **itself
  goes negative** on common-term-dominated candidate sets. Verified: a corpus where query terms
  appear in >half the docs yields `average_idf ≈ -1.10` → `eps ≈ -0.27` → all floored idfs
  negative → negative scores. The old hand-rolled `log(1 + (n-df+0.5)/(df+0.5))` is
  **unconditionally ≥ 0** (argument always > 1) — a strictly stronger invariant.
- **This is the reranker's *normal* regime, not a corner.** Rerank runs over the top-K retrieved
  candidates, selected precisely because they share the query terms → exactly the negative-idf
  regime. A query mixing a common term (floored negative) with a rare term (positive idf) produces
  mixed-sign scores with `hi > 0`; `_normalize_scores` then passes the negatives through as
  **negative normalized outputs**, breaking the strict 0..1 contract this change promises to keep.
- **Non-issue (was a listed risk):** `get_scores` returns `np.float64`, but that is a `float`
  subclass and `json.dumps` serializes it fine — the audit log is safe. Cosmetic only (`.tolist()`
  for `list[float]` purity).
- **`rank_bm25` is frozen, not maintained.** Latest release `0.2.2` (~2022), 8.6 kB pure-Python.
  Footprint is genuinely free (numpy already present via `datasketch`/`scipy` — D-FOOTPRINT holds),
  but "reuse so upstream maintains it" is hollow: there is no upstream maintenance.

**Recommendation:** lean toward declining — keep the ~20-line owned implementation; it is small,
deterministic, fully tested, and has a *stronger* numerical invariant than the library. If reuse
is still pursued, D-EPSILON must be rewritten to admit scores can go negative, and either
`_normalize_scores` must clamp (contradicting a stated non-goal) or the always-positive idf must be
preserved (defeating the reuse rationale). Left OPEN for that decision; **not** ready to apply.

---

## Context

`LexicalReranker.rerank` (`src/zeef/drivers/local.py:64-85`) is a hand-written Okapi-BM25:

```
idf = log(1 + (n - df + 0.5) / (df + 0.5))          # always positive (smoothed)
denom = tf + k1 * (1 - b + b * length / avg_len)
score += idf * (tf * (k1 + 1)) / denom
```

scored per document over query terms `q_terms = set(tokenize(query))`, then handed to
`_normalize_scores` which divides by the max so the output is 0..1 (empty → `[]`, max ≤ 0 → all
zeros). This is bespoke scoring maths on the relevance path. The swap to `rank_bm25.BM25Okapi`
removes the bespoke maths while keeping every observable property.

The replacement must be a behavioural no-op on the *contract*, not on the raw numbers. The raw
BM25 scores will differ (see D-EPSILON); what we protect — and prove — is the ordering and the
0..1 normalisation.

## Goals / Non-Goals

**Goals:**
- Replace the hand-written BM25 with `rank_bm25.BM25Okapi`, reusing a well-understood library.
- Keep the public contract byte-for-byte: signature, length/order, strict 0..1, determinism,
  air-gapped.
- Prove ordering equivalence with an adversarial test, not a self-confirming one.

**Non-Goals:**
- Changing tokenisation, `_normalize_scores`, the `k1`/`b` defaults, or `HashingEmbed`.
- Touching the `_hybrid` blend, the cloud reranker, or the selection logic.
- Matching the *raw* score values of the old implementation (impossible and unnecessary).

## Decisions

### D-FOOTPRINT — the self-build footprint argument has lapsed
The original `local.py` rationale (design.md D4 of the MVP) hand-rolled BM25 partly to keep the
sovereign profile free of heavy dependencies that "might not make the day". That argument no
longer applies:
- `datasketch>=1.6` and `scipy>=1.11` are already declared runtime dependencies in
  `pyproject.toml`, and both pull `numpy`.
- The `relate` stage runs MinHash (`datasketch`) on **every** sovereign run, so `numpy` is
  already loaded on the sovereign runtime path — it is not an optional cloud-only weight.
- `rank_bm25` is pure Python (it uses `numpy`, already present) with no native build step and no
  network. It adds no meaningful footprint on top of what MinHash already requires.

Therefore the cost side of "build vs. reuse" is effectively zero new weight, while the benefit
side (less bespoke maths to audit and maintain) is real. Reuse wins. This decision is recorded
explicitly so a future reader does not re-derive the obsolete self-build argument.

### D-DEDUP — query terms MUST be deduplicated (equivalence requirement)
The current implementation iterates `q_terms = set(tokenize(query))`, so each distinct query
term contributes exactly once regardless of repetition. `rank_bm25.BM25Okapi.get_scores(query)`
iterates the supplied query token list **without** de-duplicating: a query like `"begroting
begroting cultuur"` would count `begroting` twice and inflate documents containing it — a silent
ordering change versus today.

**Requirement:** the reranker MUST feed `get_scores(sorted(set(tokenize(query))))`. The `set`
restores once-per-term semantics; `sorted` makes the term order deterministic (defensive — BM25 is
order-independent over the query, but a fixed order keeps the call reproducible and the audit
trail stable). This is a correctness condition for equivalence, not an implementation detail, and
is asserted by a dedicated test (the repeated-term query in D-TEST).

### D-EPSILON — fix the negative-idf floor so the 0..1 invariant cannot break
Standard Okapi idf is `log((n - df + 0.5) / (df + 0.5))`, which goes **negative** when a term
appears in more than ~half the corpus. The old hand-written form used `log(1 + ...)`, which is
always positive — so per-term contributions were always ≥ 0 and `_normalize_scores` (divide by
max) always produced values in 0..1.

`rank_bm25.BM25Okapi` handles the negative-idf case by flooring: any negative idf is replaced
with `epsilon * average_idf` (default `epsilon = 0.25`), keeping all idf — and therefore all
score contributions — non-negative. This preserves our invariant: scores stay ≥ 0, so
`_normalize_scores` cannot emit a negative value.

**Requirement:** instantiate `BM25Okapi(corpus, k1=self.k1, b=self.b, epsilon=0.25)` with
`epsilon` passed **explicitly**, so the floor is pinned in our code and visible at the call site
rather than relying on a library default that a future `rank_bm25` release could change. If a
future version removes `epsilon`, the equivalence test (D-TEST, negative-idf case) fails loudly.

### D-GUARDS — preserve the existing edge-case behaviour
- Empty `docs` → return `[]` (BM25Okapi would divide by zero on an empty corpus / zero avgdl;
  guard `if not docs: return []` before constructing it, matching the current `n == 0` guard).
- A document that tokenises to nothing → its token list is `[]`; BM25Okapi handles zero-length
  docs, and `_normalize_scores` already handles an all-zero result (returns all zeros). No special
  casing beyond the empty-corpus guard.
- The return passes through the unchanged `_normalize_scores`, so the 0..1 contract is enforced in
  exactly one place, as today.

### D-TEST — adversarial equivalence, not self-confirming
The acceptance test proves ordering equivalence on cases that *could* diverge, plus a regression
anchor:

1. **Repeated-term query (D-DEDUP guard).** Query with a duplicated token (e.g. `"begroting
   begroting cultuur"`). Assert the deduped feed produces the same ordering as the single-term
   query `"begroting cultuur"` — proving the dedup fix neutralises double-counting.
2. **High-document-frequency term (D-EPSILON guard).** A query term present in **>50%** of the
   candidate documents. In standard Okapi this term has negative idf (rank_bm25 floors it to
   `epsilon * avg_idf`, positive); the old `log(1+...)` form kept it positive too. The orderings
   need not be *identical* — they are produced by different idf curves — so the test asserts the
   **new** ordering is defensible: a document that additionally contains a rare, discriminating
   query term ranks above one that contains only the common term. This is the case a
   self-confirming "they happen to agree" test would hide; we assert the new behaviour is correct
   on its own terms.
3. **Regression anchor.** Keep the existing `test_rerank_records_scores_and_reorders` assertion:
   query `"beta gamma"` → `d2` (distinct terms across a longer doc) ranks above `d1`
   (`"beta beta beta beta beta"`). This must still hold after the swap.

All three run against `BM25Okapi` + the unchanged `_normalize_scores`, so they test the real
shipped path. No comparison against a frozen copy of the old maths (that would only prove we
copied a formula, not that the behaviour is sound).

## Risks / Trade-offs

- **Raw scores change.** Accepted and documented: the contract is ordering + 0..1, not raw
  values. The audit-log records `rerank`/`bm25` scores; their absolute values will shift. This is
  visible in any stored audit trail and is called out in the CHANGELOG.
- **`rank_bm25` default drift.** Mitigated by passing `epsilon`, `k1`, `b` explicitly and pinning
  the version in `uv.lock`; the negative-idf test fails loudly if the flooring semantics change.
- **Supply chain.** `rank_bm25` is a small, long-stable, widely-used package. Procedure at apply:
  verify the pinned version's PyPI release date is older than the 7-day cooldown window, review the
  `uv.lock` diff (resolved URL, hashes), and confirm no lifecycle/build scripts run (pure Python,
  none expected).

## Migration

None. No data, no config, no API surface changes. A re-run produces the same *ordering* and the
same 0..1 range; only the raw `rerank`/`bm25` numbers in fresh audit logs differ. Existing audit
logs are historical records and are not rewritten.
