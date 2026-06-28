## Why

When the sovereign profile runs with Ollama embeddings (`ZEEF_SOVEREIGN_EMBED=ollama`), the
default model is `qwen3-embedding` — a bare tag that does not even resolve in Ollama (no
`:latest` exists), and the heaviest/slowest option benchmarked. A three-embedder comparison on
the BZK corpus (read-only, no ground truth) makes `bge-m3` the best *practical* default among the
Ollama options. This change makes it the default Ollama embed model.

**This is an explicitly PROVISIONAL choice on practical grounds — not a correctness claim.**
The comparison measured *agreement*, not *which embedder selects better* (blind corpus, no
qrels). bge-m3 is not shown to "choose better"; it is the current best practical pick.

## What Changes

- `config.py`: default `ollama_embed_model` changes from `qwen3-embedding` to `bge-m3:latest`.
- **No change to `sovereign_embed`**: the sovereign profile's default stays the deterministic,
  air-gapped `HashingEmbed` (no server, no weights). bge-m3 only takes effect when the user opts
  into Ollama via `ZEEF_SOVEREIGN_EMBED=ollama`. The air-gapped-without-a-server guarantee and the
  offline test suite are unaffected.
- Other embedders remain selectable via `ZEEF_OLLAMA_EMBED_MODEL` (e.g. `qwen3-embedding:0.6b`,
  `qwen3-embedding:4b`).

Evidence (BZK corpus, sovereign `--no-llm`, Ollama, identical query/cutoff — *agreement, not
correctness*):
- Runtime: bge-m3 **23m** vs qwen3-0.6b 29m vs qwen3-4b **1u41m**.
- GPU footprint: bge-m3 **1,21 GB** (vs 4b 3,86 GB) — lightest, fully on a 6 GB GPU.
- Score spread on the selected set comparable/sharper (median 0,69 vs 0,66/0,67).
- Caveat carried into the spec: the final default awaits a ground-truth (recall) measurement.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `provider-profiles`: add a requirement fixing the **default Ollama embed model** for the
  sovereign profile to `bge-m3:latest` (provisional), while keeping the deterministic-local
  default and env-var overridability.

## Impact

- Code: `src/zeef/config.py` (one default value).
- Behaviour: only affects sovereign runs that already opt into `ZEEF_SOVEREIGN_EMBED=ollama`;
  no change to the default sovereign path or to cloud.
- Tests: assert the new default + that the env-var override still wins + that the default
  sovereign profile still resolves `HashingEmbed`.
- Docs: README/CHANGELOG note bge-m3 as the provisional default Ollama embedder.
