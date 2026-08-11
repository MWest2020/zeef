## ADDED Requirements

### Requirement: Default sovereign Ollama embed model

When the sovereign profile uses Ollama embeddings, the system SHALL default the Ollama embed model to `bge-m3:latest`, and this default SHALL be overridable via the `ZEEF_OLLAMA_EMBED_MODEL` environment variable. This is a provisional default chosen on practical grounds (lowest runtime and GPU footprint, and comparable/sharper score spread in an agreement-only comparison on the Woo corpus); it is NOT a claim that bge-m3 selects more relevant documents, and the final default awaits a ground-truth (recall) measurement.

Changing this default SHALL NOT change the sovereign profile's default embedder: with no `ZEEF_SOVEREIGN_EMBED=ollama` opt-in, the sovereign profile MUST still resolve the deterministic, air-gapped local embedder (no server or weights required).

#### Scenario: Ollama opt-in uses bge-m3 by default

- **WHEN** the sovereign profile is resolved with `ZEEF_SOVEREIGN_EMBED=ollama` and no
  `ZEEF_OLLAMA_EMBED_MODEL` set
- **THEN** the embedding provider is Ollama with model `bge-m3:latest`

#### Scenario: Env-var overrides the default

- **WHEN** `ZEEF_OLLAMA_EMBED_MODEL` is set (e.g. `qwen3-embedding:0.6b`) with
  `ZEEF_SOVEREIGN_EMBED=ollama`
- **THEN** the embedding provider uses the env-var model, not the default

#### Scenario: Default sovereign stays air-gapped

- **WHEN** the sovereign profile is resolved without `ZEEF_SOVEREIGN_EMBED=ollama`
- **THEN** the embedding provider is the deterministic local embedder, requiring no server or
  network
