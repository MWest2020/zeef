# Changelog

Alle noemenswaardige wijzigingen aan dit project worden hier vastgelegd.
Formaat losjes gebaseerd op [Keep a Changelog](https://keepachangelog.com/nl/);
versies volgen [SemVer](https://semver.org/lang/nl/).

## [Unreleased]

### 2026-06-17 — Projectinitiatie

**Wat:** repo opgezet, OpenSpec change #1 (`converge-mvp`) opgesteld en gevalideerd,
projectscaffold, Q&A-document, documentatie-site (Hugo) en HTML-presentatie aangezet.

**Waarom:** kickoff voor de technische verkenning Woo (BZK/ECP) op 26 juni 2026. De tool moet
die dag op een aangeleverde dataset + verfijnde zoekvraag draaien en een navolgbare selectie
opleveren.

**Toegevoegd:**
- Private GitHub-repo `MWest2020/zeef`; lokale git op `main`.
- OpenSpec geïnitialiseerd (schema `spec-driven`). Change `converge-mvp` met `proposal.md`,
  `design.md`, 10 capability-specs en `tasks.md` — `openspec validate --strict` slaagt (4/4
  artefacten compleet).
- Projectscaffold: `uv`-project (Python 3.12+), `pyproject.toml` met core-deps (pydantic v2,
  typer, rich, openpyxl) en optionele extras `sovereign`/`cloud`/`dev`.
- Canoniek datamodel `src/zeef/models.py` (`Document`, `Chunk`, `Relation`, content-geadresseerde
  id), interfaces `src/zeef/protocols.py` (`Loader`, `EmbeddingProvider`, `RerankerProvider`,
  `LLMProvider`), profielconfig `src/zeef/config.py` (incl. `NullLLM` voor `--no-llm`),
  audit-writer `src/zeef/audit.py` (append-only JSONL), CLI-skelet `src/zeef/cli.py`
  (`zeef converge` met cutoff-vlagvalidatie).
- Rooktests (`tests/test_models.py`) — 3 passed.
- `LICENSE` (EUPL-1.2, officiële SPDX-tekst), `README.md`, `.gitignore`.
- `hackathon/qa-technische-verkenning.md` — levend Q&A-document voor 26 juni.
- Documentatie-site (Hugo) in `docs/` en HTML-presentatie in `presentation/`.

**Licentie:** EUPL-1.2 (aansluitend bij Common Ground / NL-overheid).

**Tests:** `uv run pytest` → 3 passed.

**Nog te doen:** implementatie van de stages volgens `openspec/changes/converge-mvp/tasks.md`.
