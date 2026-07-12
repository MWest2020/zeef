# Change: apply-docs-contract

> Seed-change, aangeleverd vanuit Westmarch (personal-handbook, change 2
> add-docs-contract). Uitvoering door een habitat-builder-Job; merge door Mark.

## Why

zeef is NLnet-traject-repo; docs-reviewbaarheid voor grant-reviewers is de deadline-druk. De huidige docs/ is een Hugo-site — het handbook aggregeert platte markdown volgens het contract.
Zonder uniform contract is handbook-aggregatie zinloos: het handbook (hub)
importeert `docs/` van dit repo at build time.

## What changes

- `docs/` volgens het contract hieronder (additief + migratie van bestaande
  docs; geen verwijderingen buiten wat hieronder expliciet staat).
- `.mcp.json` in de root volgens template (handbook-URL blijft placeholder
  `TODO-change-3`).
- Géén andere wijzigingen. Eén branch, één PR, titel:
  `docs: apply handbook docs contract`.

## Docs-contract (bindend, uit Westmarch add-docs-contract)

```
docs/
  index.md          # wat is dit, status, max 3 regels boilerplate
  how-to/           # taakgericht
  reference/        # feiten (config, API, schema's)
  explanation/      # waarom-besluiten; ADR's onder explanation/adr/NNNN-titel.md
```

- Lege mappen weglaten. Minimum viable: `index.md` + één reference-pagina.
- Front matter per pagina (YAML): `status: current|draft|deprecated` +
  `last_reviewed: <ISO-datum>`. GEEN `owner`-veld.
- Gemigreerde pagina's zonder inhoudelijke review: `status: draft`,
  `last_reviewed` = migratiedatum. Alleen een echte review zet `current`.
- Eén taal per repo (deze repo: Nederlands).
- README blijft; `docs/index.md` verwijst ernaar, vervangt niet.
- Bestaande losse docs migreren; stub met verwijzing achterlaten op de oude
  plek als er externe links naartoe kunnen bestaan.


## Repo-specifiek

- `docs/` bevat nu een Hugo-site (`docs/content/docs/*.md`, `hugo.yaml`,
  `go.mod`). Migreer de INHOUD van `docs/content/docs/` naar de
  contractstructuur: `wat-is-zeef.md`/`architectuur.md` → `explanation/`,
  `aan-de-slag.md` → `how-to/`, `de-pijplijn.md`/`audit-trail.md` →
  `reference/`, `roadmap.md`/`bijdragen.md` → root of `explanation/`.
- `docs/pipeline/scope-filter.md` → `reference/`.
- De Hugo-toolchain (hugo.yaml, go.mod, go.sum, thema-config) NIET weggooien:
  verplaats naar `site/` met een stub-README, of laat een taak-notitie achter
  als dat conflicteert — Mark beslist over definitieve verwijdering.
- Taal: Nederlands (privaat repo).

## Non-goals

- Geen merge (Mark merget), geen scope buiten deze change, geen wijzigingen
  aan CLAUDE.md / .claude/agents/ / CI.
