# Habitat reviewer — apply-docs-contract

_run_id reviewer-apply-docs-contract-20260712-183929 · verdict ok · 2026-07-12T18:41:19Z_

---

Ik heb de diff van de change `apply-docs-contract` beoordeeld tegen de reviewer-contractchecks. Hieronder mijn verdict. Ik ben read-only: ik fix niets en open de PR niet (dat is taak 4.1 → Mark).

---

## Verdict: **PASS** ✅

Change `apply-docs-contract` — substantiële diff in commit `b4a560f` (`docs: apply handbook docs contract`).

### 1. Scope ✓
De docs-commit doet precies de tasks: Hugo-toolchain + content verplaatst naar `site/` met stub-README (`site/README.md:1`), inhoud gemigreerd naar `docs/{how-to,reference,explanation}`, `docs/pipeline/scope-filter.md` → `docs/reference/scope-filter.md`, `tasks.md` afgevinkt. `.mcp.json` ongewijzigd met placeholder (`.mcp.json:5` → `"url": "TODO-change-3"`), conform taak 2.4. Geen productiecode-, test- of `src/`-wijzigingen.

### 2. Contract (Diátaxis-light) ✓
- **Alleen toegestane mappen dragen markdown**: `docs/` bevat enkel `index.md` + `how-to/` + `reference/` + `explanation/` (9 pagina's). Geen markdown buiten die structuur.
- **Front matter op elke pagina**: alle 9 hebben `status: draft` + `last_reviewed: 2026-07-12`, **geen `owner`** — geverifieerd op alle bestanden.
- **Eén taal**: consistent Nederlands.
- **README blijft, wordt niet vervangen**: `docs/index.md:16` verwijst naar `../README.md`. ✓
- **Geen dangling links / geen Hugo-shortcodes**: alle interne `.md`-links resolven, alle ankers (`#positionering`, `#engineeringfilosofie`, `#profielen`) bestaan, geen `{{ }}`-shortcodes in `docs/`.
- Geen lege mappen; alle drie de secties hebben inhoud (minimum viable ruim gehaald).

### 3. Cage intact ✓
Diff raakt **niet** `CLAUDE.md` (niet aanwezig), `.claude/agents/`, of CI/workflow-config. Geverifieerd op de volledige `main...HEAD` naamlijst.

### 4. Geen secrets ✓
Enige match in de secret-scan is een *documentatiezin* (`docs/explanation/architectuur.md` → "Geheimen … komen uit env / SOPS+age, **nooit** uit code") — dat is beleid dat wordt beschreven, geen gelekt credential. Geen tokens, keys of secret-dragende URLs.

---

### Observatie (geen fail)
Commit `4ed956a` (author *Habitat builder*) voegt `.habitat/run-output-*.md`, `.habitat/run-report-*.html` en `run-report.json` toe. Dat valt formeel buiten de change-scope ("géén andere wijzigingen"), maar het zijn door de habitat-harness gegenereerde run-logs (analoog aan CI-artefacten), in een aparte wrapper-commit los van de builder-content. Niet blokkerend — ik meld het puur zodat Mark het bewust meeneemt bij de merge.

**Advies:** klaar voor taak 4.1 (Mark opent PR + merget). Titel conform contract: `docs: apply handbook docs contract`.
