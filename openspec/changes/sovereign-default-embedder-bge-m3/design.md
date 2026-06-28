## Context

`_resolve_embed_rerank` (profiles.py) picks the sovereign embedder from `settings.sovereign_embed`:
`"local"` → `HashingEmbed` (default, air-gapped), `"ollama"` → `OllamaEmbed(host,
settings.ollama_embed_model)`. Only the latter reads `ollama_embed_model`, whose default is
`qwen3-embedding`. This change retargets that one default.

## Goals / Non-Goals

**Goals:**
- Make `bge-m3:latest` the default Ollama embed model, so opting into Ollama gets the best
  practical option without an env-var.
- Keep the change minimal, reversible, and overridable via `ZEEF_OLLAMA_EMBED_MODEL`.

**Non-Goals:**
- Changing the sovereign profile's default embedder (stays `HashingEmbed` / air-gapped).
- Any claim that bge-m3 selects more relevant documents (no ground truth).

## Decisions

### Decision: change only `ollama_embed_model`, not `sovereign_embed`

The benchmark compared Ollama embedders to each other, not to the hashing default, and the
air-gapped-without-a-server property is a documented design guarantee. So the deterministic-local
default is preserved; bge-m3 is the default *within* the Ollama path only.

### Decision: pin the explicit `:latest` tag

The old default `qwen3-embedding` had no resolvable tag. `bge-m3:latest` is the pulled, resolvable
tag, so the default works out of the box where Ollama has bge-m3.

### Decision: encode "provisional" in the spec, not just the changelog

The requirement text states the choice is provisional (speed/footprint/agreement) and that the
final default awaits a ground-truth measurement, so the rationale survives in the spec, not only
in a commit message.

## Risks / Trade-offs

- [User on Ollama path silently gets a different model than before] → It only affects opt-in
  Ollama runs; documented in README/CHANGELOG; any prior model stays reachable via the env-var.
- [bge-m3 had more embed-500/nulvector fallbacks in the BZK run (3 vs 1)] → Noted as a known
  caveat; it does not change the practical speed/footprint case and is orthogonal (a driver-level
  logging concern already tracked separately).
