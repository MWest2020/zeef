## Context

`src/zeef/drivers/cloud.py` ships the cloud profile's Voyage embedder and reranker. Their bodies
are minimal:

```
class VoyageEmbed:
    def embed(self, texts):
        res = self._client._post("/embeddings", {"model": self.model, "input": texts})
        return [[float(x) for x in row["embedding"]] for row in res["data"]]

class VoyageReranker:
    def rerank(self, query, docs):
        res = self._client._post("/rerank", {"model": ..., "query": query, "documents": docs})
        ...
```

No batching, no truncation, no retry. `_VoyageClient._post` uses `urllib.request.urlopen`, which
raises `HTTPError` on a 4xx — uncaught, so a single over-limit request aborts the whole run.

Three pipeline call sites pass the full candidate set straight through:
- `relate` → `dedup.py:56` — `embed.embed([d.text for d in targets])` over every non-empty doc.
- `rerank` → `rerank.py:25` — `reranker.rerank(query, [d.text for d in candidates])`.
- `retrieve` → `retrieve.py:70` — `embed.embed([c.text for c in chunks])` per document.

On the observed corpus (414 PDFs, 1.7 GB) the `relate` call is the first to exceed Voyage's
per-request token budget, and any single large PDF can exceed the per-input token cap; either
returns HTTP 400 for the whole batch. The sovereign Ollama embedder already solves the per-input
problem with a character budget (`ollama_embed_chars=8000`); the Voyage drivers never got the
equivalent, nor batching across inputs.

The fix is a transport-layer concern only. Selection semantics — one vector/score per input, in
input order, feeding the existing rerank/score/select chain — must be a behavioural no-op.

## Goals / Non-Goals

**Goals:**
- Make `VoyageEmbed.embed` and `VoyageReranker.rerank` complete on a realistic corpus by bounding
  each request to the provider's documented limits.
- Keep the `embed`/`rerank` contract byte-for-byte: one vector/score per input, in input order.
- Make truncation a visible, audited variable — never silent.
- Record the applied limits in the run manifest.

**Non-Goals:**
- Char-cap *parity* with the sovereign run (no cloud run is scheduled; nothing to compare).
- Retries/back-off on transient 5xx (separate hardening concern).
- The `ClaudeLLM` driver (one prompt per call already).
- Changing which stages call the cloud providers, or the selection logic.
- Matching raw embedding/rerank values to any prior run (there is no prior cloud run).

## Decisions

### D-CENTRAL — fix inside the drivers, not the pipeline
Truncation and batching live entirely inside `VoyageEmbed.embed` / `VoyageReranker.rerank` (and a
shared helper on `_VoyageClient`). All three call sites (`relate`, `retrieve`, `rerank`) route
through these methods, so a single transport-layer fix covers all three with **no pipeline
change**. This keeps the selection semantics provably untouched: the methods still return one
vector/score per input in input order, so `dedup`, `retrieve`, `rerank`, `score` and `select` see
exactly the same contract.

### D-LIMITS — defaults are PROVISIONAL and MUST be verified before merge
The proposed defaults below are conservative starting points, **not** authoritative Voyage
limits. Before any implementation, the actual current per-request and per-input limits for the
configured models (`voyage-3` embeddings, `rerank-2`) MUST be read from the Voyage documentation
and the defaults reconciled to them. Do not assume the numbers in this table are correct.

| Setting | Provisional default | Bounds | Verify against |
|---|---|---|---|
| `voyage_embed_chars` | 24000 (~6K tok) | per-input truncation | voyage-3 per-input token cap |
| `voyage_rerank_chars` | 8000 | per-input truncation | rerank-2 per-doc/context limit |
| `voyage_batch_size` | 128 | max inputs per request | per-request input-count limit |
| `voyage_batch_chars` | 480000 (~120K tok) | cumulative chars per request | per-request total-token budget |

All four are `Settings` fields with `ZEEF_` env overrides, so the verified values can be pinned
without a code change, and the run manifest records what was actually applied.

### D-RERANK-SPLIT — the rerank batching assumption is UNCONFIRMED (open, gates merge)
Batching the **embedder** is safe: each input embeds independently, so splitting the input list
and concatenating vectors in order is exact.

Batching the **reranker** is **only safe if** Voyage returns an *absolute* relevance score for
each `(query, document)` pair, **independent of the other documents in the same request**. If
that holds, the candidate list can be split across requests and the per-document scores
reassembled in original index order without distortion.

This independence is **assumed, not verified.** It MUST be confirmed against the Voyage rerank
documentation before any rerank batching is implemented.

- **If confirmed** — rerank batches like the embedder (split by count + char budget, reassemble
  by original index).
- **If the score is batch-relative** (normalised within a request, or otherwise dependent on the
  batch composition) — rerank **cannot** be split without changing results. The fallback is
  **truncation-only**: shrink each document with `voyage_rerank_chars` so the full candidate set
  fits in a single request, and if it still cannot fit, fail loudly with a clear message rather
  than silently splitting. The plan for rerank then differs materially from the embedder plan.

**Risk if assumed wrong and shipped:** silently incorrect rerank scores → a different, unexplained
top-100 with no error. This is exactly the kind of silent correctness bug "boring and auditable"
must refuse. Hence: verify first, branch the rerank design on the answer, do not assume.

### D-AUDIT — truncation is a visible variable, not a silent one
- The applied limits (`voyage_embed_chars`, `voyage_rerank_chars`, `voyage_batch_size`,
  `voyage_batch_chars`) are added to `run-manifest.json` under `params` (`run.py:177-189`), so a
  reader knows the transport bounds the run actually used.
- When truncation **fires** (at least one input exceeded its char budget), the driver emits a
  `truncation` audit event recording: the stage/endpoint, how many inputs were truncated, and the
  maximum original length seen. So the audit trail shows *that* text was dropped and *how much*,
  not merely that a cap was configured.
- The driver needs no `AuditLog` reference of its own: it exposes counters/attributes that the
  calling stage (or `run.py`) reads and logs, keeping the driver free of pipeline coupling. The
  exact wiring is an implementation detail for the apply phase.

### D-CHARCAP — future overlap reporting duty (no decision now)
If a cloud↔sovereign selection-overlap is ever measured, the report MUST state **both** character
caps from **both** run manifests (cloud `voyage_embed_chars` vs sovereign `ollama_embed_chars`),
because the two runs see different amounts of each document's text. Truncation is then a known,
traceable factor in the overlap rather than a hidden asymmetry — on top of the full-stack
asymmetry (Voyage+Haiku vs qwen3+Ollama) that already prevents any clean "sovereign ≈ cloud"
claim. **No char-cap parity is decided here**: no cloud run is scheduled, so there is nothing to
compare yet. This decision only records the reporting obligation for whenever such a run happens.

### D-NO-RETRY — retries are out of scope
This change bounds request *size*. Transient 5xx/network retry-and-back-off is a separate concern
and is explicitly not addressed, to keep the change small and auditable. A 4xx from exceeding a
limit should not happen once the bounds are correct; if one still occurs, failing loudly is
preferred over masking it with retries.

## Risks / Trade-offs

- **Provisional limits wrong (D-LIMITS).** Mitigated by treating the defaults as unverified and
  requiring reconciliation with the live Voyage docs before merge; all four are env-overridable.
- **Rerank split assumption wrong (D-RERANK-SPLIT).** The dominant risk: a silent correctness bug.
  Mitigated by gating implementation on documentation verification and branching the design.
- **Truncation changes embeddings.** Accepted and made visible: dropping text past the char cap
  changes vectors/scores versus full text. Recorded in the manifest and audited per run; relevant
  only to a future overlap report (D-CHARCAP), which must disclose it.
- **More requests, more cost/latency.** Batching turns one (failing) request into several
  succeeding ones; more Voyage calls and tokens. Accepted — correctness over a single call.

## Migration

None. No data, no stored config, no public API change. The drivers were never live-tested, so no
existing cloud run's behaviour is altered. The first successful cloud run is enabled by this
change, not migrated.
