# Tasks: apply-docs-contract

- [x] 1.1 Branch `docs/contract` vanaf de default branch.
      _(Uitgevoerd op de habitat-werkbranch `habitat/builder/apply-docs-contract`,
      die van de default branch is afgeleid; geen aparte `docs/contract` aangemaakt
      om het merge-/PR-proces van de habitat niet te doorkruisen — Mark merget.)_
- [x] 2.1 `docs/`-structuur aanleggen volgens het contract; bestaande docs
      migreren zoals beschreven in proposal.md (repo-specifiek); stubs
      achterlaten waar externe links kunnen bestaan.
      _(Hugo-toolchain + content verplaatst naar `site/` met stub-README;
      inhoud gemigreerd naar `docs/{how-to,reference,explanation}` als platte
      markdown. Géén stub voor `docs/pipeline/scope-filter.md`: dat bestand
      hoorde niet bij de gepubliceerde Hugo-site en heeft dus geen externe
      URL — een stub zou bovendien het contract schenden (alleen toegestane
      submappen dragen markdown).)_
- [x] 2.2 Front matter op elke pagina: gemigreerd-zonder-review =
      `status: draft` + `last_reviewed` = migratiedatum.
      _(Alle 9 pagina's: `status: draft`, `last_reviewed: 2026-07-12`, geen `owner`.)_
- [x] 2.3 `docs/index.md`: één alinea wat het project is, status, link naar
      README, links naar de aanwezige secties.
- [x] 2.4 `.mcp.json` in de root plaatsen (template uit de seed; placeholder `TODO-change-3` laten staan).
      _(Reeds aanwezig uit de seed; template klopt, placeholder `TODO-change-3` behouden.)_
- [x] 3.1 Zelfcheck tegen het contract: alleen toegestane submappen dragen
      markdown, elke pagina heeft front matter, één taal (Nederlands).
      _(Geverifieerd: geen Hugo-shortcodes meer in `docs/`, alle interne
      `.md`-links resolven, alleen `how-to/`/`reference/`/`explanation/` + `index.md`.)_
- [ ] 4.1 PR openen met titel `docs: apply handbook docs contract`; body vinkt
      per contractpunt af wat is toegepast + vermeldt de punten die de
      proposal als "PR-body" markeert. STOP daarna: Mark merget.
