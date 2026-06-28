## 1. Default

- [x] 1.1 `src/zeef/config.py`: change `ollama_embed_model` default from `"qwen3-embedding"` to `"bge-m3:latest"` (keep `sovereign_embed` = `"local"` unchanged)

## 2. Tests

- [x] 2.1 `tests/test_profiles.py`: assert `Settings().ollama_embed_model == "bge-m3:latest"`
- [x] 2.2 Assert sovereign + `sovereign_embed="ollama"` resolves an Ollama embedder whose name is `ollama:bge-m3:latest`
- [x] 2.3 Assert `ZEEF_OLLAMA_EMBED_MODEL` override still wins (e.g. `qwen3-embedding:0.6b`)
- [x] 2.4 Confirm the existing test that the default sovereign profile resolves `HashingEmbed` still passes (air-gapped default intact)

## 3. Docs & changelog

- [x] 3.1 README: note bge-m3 is the provisional default Ollama embed model under `ZEEF_SOVEREIGN_EMBED=ollama`, overridable via `ZEEF_OLLAMA_EMBED_MODEL`
- [x] 3.2 Dated `CHANGELOG.md` entry — what/why, explicit "provisional, agreement-not-correctness", files, test result

## 4. Verify

- [x] 4.1 `ruff` + offline suite green; all files ≤200 lines
