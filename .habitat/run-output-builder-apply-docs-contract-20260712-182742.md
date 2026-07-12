# Habitat builder — apply-docs-contract

_run_id builder-apply-docs-contract-20260712-182742 · verdict ok · 2026-07-12T18:34:41Z_

---

The change is committed. Here's my run report.

## Run report — `apply-docs-contract` (builder)

**Branch:** `habitat/builder/apply-docs-contract` · **Commit:** `b4a560f` `docs: apply handbook docs contract`

### Wat is gedaan

**`docs/` volgens het contract** — platte markdown, één taal (Nederlands):
```
docs/
  index.md                         # wat/status/link README + secties
  how-to/aan-de-slag.md
  reference/de-pijplijn.md
  reference/audit-trail.md
  reference/scope-filter.md        # git-mv vanuit docs/pipeline/
  explanation/wat-is-zeef.md
  explanation/architectuur.md
  explanation/roadmap.md
  explanation/bijdragen.md
```
- Inhoud gemigreerd uit de Hugo-content; alle Hugo-shortcodes (`{{< callout >}}`, `{{< cards >}}`, hero-blokken) omgezet naar platte markdown; interne links herbedraad naar de nieuwe structuur (geverifieerd: 0 gebroken `.md`-links, 0 resterende shortcodes).
- **Front matter** op elke pagina: `status: draft` + `last_reviewed: 2026-07-12`, **géén `owner`** (conform contract voor gemigreerd-zonder-review).

**Hugo-toolchain behouden, niet weggegooid** — `hugo.yaml`, `go.mod`, `go.sum`, `content/`, `CONTENT.md`, `.gitignore` → `site/`, met `site/README.md` als stub die de relocatie uitlegt en `docs/` als leidend markeert. Definitieve verwijdering laat ik aan Mark.

**`.mcp.json`** — al aanwezig uit de seed en klopt met de template; placeholder `TODO-change-3` behouden.

### Afwijkingen / oordelen (voor review)
1. **Branch:** ik werk op de habitat-branch `habitat/builder/apply-docs-contract` (afgeleid van default), niet op een aparte `docs/contract` — om het PR-/merge-proces van de habitat niet te doorkruisen.
2. **Geen stub voor `docs/pipeline/scope-filter.md`:** dat bestand hoorde niet bij de gepubliceerde Hugo-site (het lag buiten `content/`, dus geen publieke URL) en het is een privaat repo — de "externe links kunnen bestaan"-voorwaarde geldt niet. Een stub zou bovendien het zelfcheck-punt schenden dat alléén toegestane submappen markdown dragen. Git-historie blijft behouden via de `git mv` naar `reference/`.
3. **Root `.gitignore` ongemoeid gelaten** (scope: "géén andere wijzigingen"). De Hugo build-output-regels erin (`docs/public/` etc.) zijn nu stale maar onschadelijk; de site-lokale ignore-regels staan in `site/.gitignore`. Punt voor Mark om eventueel later op te ruimen.

### Openstaand — taak 4.1 (PR openen)
`gh` is niet geïnstalleerd en er zijn geen push-credentials, dus ik kan de PR niet zelf openen. Werk staat gecommit op de branch. **STOP hier: Mark merget.** Klaargezette PR-inhoud:

> **Titel:** `docs: apply handbook docs contract`
>
> **Body — contractpunten toegepast:**
> - [x] `docs/` = `index.md` + `how-to/` + `reference/` + `explanation/`; lege mappen weggelaten
> - [x] Front matter per pagina: `status` + `last_reviewed`, géén `owner`
> - [x] Gemigreerd zonder review → `status: draft`, `last_reviewed: 2026-07-12`
> - [x] Eén taal (Nederlands)
> - [x] README blijft; `docs/index.md` verwijst ernaar (vervangt niet)
> - [x] Bestaande docs gemigreerd; Hugo-toolchain naar `site/` i.p.v. weggegooid
> - [x] `.mcp.json` = seed-template, placeholder `TODO-change-3` behouden
>
> **PR-body-aandachtspunten (zie afwijkingen hierboven):** branchnaam, ontbrekende `pipeline/`-stub, ongemoeide root-`.gitignore`, en de definitieve verwijdering van `site/` die aan Mark is.
