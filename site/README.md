# site/ — gearchiveerde Hugo-documentatiesite

Deze map bevat de **voormalige** zeef-documentatiesite (Hugo + Hextra), verplaatst
vanuit `docs/` bij het toepassen van het handbook-docs-contract (OpenSpec-change
`apply-docs-contract`).

De canonieke, reviewbare documentatie leeft nu als platte markdown onder
[`../docs/`](../docs/) volgens het contract (`index.md` + `how-to/` + `reference/` +
`explanation/`). De inhoud hieronder is **gemigreerd** naar die structuur; deze
Hugo-site is bewust **niet weggegooid** zodat de toolchain behouden blijft.

> **Definitieve verwijdering beslist Mark.** Zolang deze map bestaat, is de
> plattemarkdown-versie onder `docs/` leidend; `site/content/` is een historische kopie.

## Wat hier staat

- `hugo.yaml`, `go.mod`, `go.sum` — de Hugo-toolchain (Hextra via Hugo Modules).
- `content/` — de oorspronkelijke Hugo-content (Nederlands).
- `CONTENT.md` — de oorspronkelijke Hugo-auteursgids.
- `.gitignore` — Hugo build-output en module-cache (site-lokaal).

## Lokaal draaien

    cd site
    hugo server          # live-reload op http://localhost:1313
    hugo --gc --minify   # productiebuild (output in site/public/, ge-gitignored)

Zie `CONTENT.md` voor het toevoegen van pagina's aan de Hugo-site.
