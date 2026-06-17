## Context

`zeef` performs the convergence step of the Woo process: ~1.000 semi-relevant documents in,
~100 core-relevant out, with full traceability. The engineering philosophy is a hard
requirement: **boring and auditable over fast or clever**, nothing that cannot be explained
in an ISO 27001 context. Deterministic where possible; LLM only where necessary and always
logged. Every selection and exclusion decision must be reproducible and traceable afterwards.

The methodological prior art is e-discovery / TAR (technology-assisted review). We adopt its
recall-oriented stance (missing a relevant document is worse than including noise) rather than
designing relevance ranking from first principles.

Current state: greenfield. No existing code or specs. This design fixes the data model, the
provider abstraction, and the stage contracts that the specs and tasks build on.

## Goals / Non-Goals

**Goals:**
- One canonical `Document` model as the spine; every loader normalizes to it.
- A pipeline of independently runnable, independently logged stages.
- Two interchangeable provider profiles (`cloud`, `sovereign`) selected by a single flag, plus
  a `--no-llm` fallback for maximum sovereignty / air-gapped safety.
- Configurable, non-magic selection cutoff (`top-n` / `threshold` / `target`) with explicit
  recall bias.
- An append-only JSONL audit-trail from which both the selected core and the excluded rest are
  fully reconstructable — including which model ran and *where* (local/cloud), and the exact LLM
  prompt where applicable.

**Non-Goals (this change):**
- Scanned-PDF OCR and the multimodal VL-reranker driver.
- Clustering, summarization, and highlighting (the `enrich` stage).
- Any web UI, connectors (M365/DMS/case systems), or the redaction phase (phase 3).
- Distributed/streaming processing — a single-machine batch run over a local folder is enough
  for ~1.000 documents.

## Decisions

### D1 — One canonical `Document` model (pydantic v2)
Every input file is normalized to a single model so all downstream stages are format-agnostic
(the role `CertBundle` plays in `certswap`). Stages read and write the same object; scores and
decisions accumulate on it.

```python
class Chunk(BaseModel):
    id: str                       # f"{document_id}:{ordinal}"
    ordinal: int
    text: str
    embedding: list[float] | None = None

class Relation(BaseModel):
    kind: Literal["thread-parent", "attachment-of", "duplicate-of", "overlaps-with"]
    target_id: str                # id of the related Document
    evidence: str                 # why this relation was asserted (header value, hash, cosine)

class Document(BaseModel):
    id: str                       # stable content+origin hash (see D2)
    source_path: str
    doc_type: Literal["email", "pdf_digital", "pdf_scanned", "office", "other"]
    metadata: dict[str, Any]      # date, sender, subject, source-system, message-id, ...
    text: str                     # normalized text (after OCR where applicable)
    chunks: list[Chunk] = []      # only for embedding/rerank of long docs
    relations: list[Relation] = []
    scores: dict[str, float] = {} # per-stage: embed_sim, rerank, final, ...
    decision: Literal["selected", "out_of_scope", "undecided"] = "undecided"
    decision_reason: str = ""     # human-readable justification
```

*Alternative considered:* a thin row + sidecar files per stage. Rejected — harder to reason
about and audit than one object that carries its full provenance.

### D2 — Content-addressed, stable `id`
`id = sha256(normalized_text + source_path).hexdigest()[:N]`. Deterministic, so a re-run yields
the same ids (reproducibility), and exact-duplicate bodies surface naturally. The origin path is
mixed in so two genuinely distinct files with identical text are still distinguishable; the
`duplicate-of` relation (D5) handles the "same content, different path" case explicitly rather
than silently collapsing ids.

### D3 — All interfaces are Protocols in `protocols.py`; drivers live separately
`Loader`, `EmbeddingProvider`, `RerankerProvider`, `LLMProvider`. Concrete drivers
(`drivers/ollama.py`, `drivers/claude.py`, `drivers/eml_loader.py`, …) are selected by the
profile, never imported directly by pipeline stages. This is what makes `cloud` ↔ `sovereign`
a flag, not a code change.

```python
class LLMProvider(Protocol):
    def complete(self, prompt: str, *, system: str | None = ...) -> str: ...
class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
class RerankerProvider(Protocol):
    def rerank(self, query: str, docs: list[str]) -> list[float]: ...   # score per doc
class Loader(Protocol):
    def can_load(self, path: Path) -> bool: ...
    def load(self, path: Path) -> list[Document]: ...  # list: an .eml yields body + attachments
```

### D4 — Profiles as a resolved set of drivers
A `Profile` (pydantic settings) maps `--profile {cloud,sovereign}` to a concrete
`(LLMProvider, EmbeddingProvider, RerankerProvider)` triple. `--no-llm` swaps `LLMProvider` for a
`NullLLM` that raises if called and makes the scope-filter use rules only and selection use
embed+rerank only. The pipeline code receives providers by injection and never knows which
profile is active. Secrets (cloud API keys) come from env / SOPS+age, never from code or config
files. `sovereign` asserts default-deny egress: no network calls leave the machine.

### D5 — Deterministic-first relate & scope-filter, LLM as a logged fallback
- **Threads:** built purely from RFC 5322 headers (`Message-ID` / `In-Reply-To` / `References`).
  No headers → degrade to a logged heuristic, explicitly marked as heuristic in the evidence.
- **Near-duplicates:** MinHash/SimHash candidate generation, confirmed by embedding cosine above
  a threshold. Exact duplicates via the D2 hash.
- **Scope-filter:** an ordered list of deterministic rules (forwarded-only mail, calendar
  invites, process notifications, earlier mails already represented by a thread head, duplicates)
  runs first. Only documents no rule decides are sent to the LLM, and only in `cloud`/non
  `--no-llm` runs. Every decision — rule or LLM — writes a `decision_reason` and an audit event.

*Why:* deterministic rules are auditable and reproducible by construction; the LLM is the
expensive, harder-to-explain path, so it handles the minimum residue and always leaves a prompt
in the log.

### D6 — Selection: three explicit cutoff modes, recall-biased
`--top-n N` (hard count), `--threshold X` (final score ≥ X), `--target N` (adaptive threshold
aiming at ~N, reporting where the score "knee" is so the user chooses consciously rather than
accepting a magic number). A configurable recall bias widens the cut on ties / near-threshold
docs toward inclusion. The chosen mode and its parameters are logged.

### D7 — Audit-trail is append-only JSONL, one event per stage action
Structured logging only (no ad-hoc prints). Each event: timestamp, stage, document id(s),
action, inputs (query, thresholds), model id + location (`local`/`cloud`), and the exact prompt
for LLM steps. The log is the source of truth for the "transparency" criterion and the pitch.

### D8 — Files ≤ 200 lines
Hard constraint from the brief. Drives the split: one file per loader, per driver, per stage;
`protocols.py` holds only interfaces; `models.py` only the data model.

## Risks / Trade-offs

- **No email headers in the delivered data** → thread reconstruction becomes heuristic, not fact.
  *Mitigation:* detect header absence at ingest, mark thread relations as `heuristic` in evidence,
  and surface this prominently in the audit-log and inventory. (Open Q1 to the dataset owner.)
- **Recall bias inflates the selection** beyond the target. *Mitigation:* the bias is explicit and
  tunable; `--target` shows the knee so the user trades off consciously.
- **LLM nondeterminism undermines reproducibility.** *Mitigation:* temperature 0 where the provider
  allows, full prompt + model id + location logged, and `--no-llm` gives a fully deterministic run.
- **`uv` / local-model footprint** (Qwen3 weights, GPU) may not fit the day's hardware.
  *Mitigation:* `--no-llm` sovereign path needs only an embedding + cross-encoder model; `cloud`
  is the benchmark when egress is allowed. (Open Q to environment owner.)
- **200-line cap encourages fragmentation.** *Mitigation:* split along natural seams (one
  driver/stage per file); accept slightly more files for far easier review.

## Migration Plan

Greenfield — no migration. Deployment for 26 June: `uv sync`, pull the sovereign models locally
ahead of the day, dry-run on a representative sample if one is provided. Rollback is trivial (no
state, outputs are written to a fresh run directory each time).

## Open Questions

- **Q1 (blocking ingest):** Are the ~1.000 docs delivered as original `.eml`/`.msg` with intact
  headers, or rendered/printed PDF? Mixed? Determines whether threads are fact or heuristic.
- **Q2:** Are PDFs digital (text layer) or scanned (would need the out-of-scope OCR path)?
- **Q3:** Is the environment air-gapped, or is egress to a cloud API allowed on the day?
- **Q4:** How is "missing a relevant doc" weighted vs. "noise in the selection"? Sets the default
  recall bias.

These mirror the [P1] questions in the 24 June Q&A; defaults are assumed and made explicit in the
pitch if unanswered (mixed format, recall-dominant, air-gapped-primary, `--target` adaptive).
