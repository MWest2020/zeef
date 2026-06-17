# Documentatiesite (Hugo + Hextra)

Deze map bevat de zeef-documentatiesite. Thema: **Hextra**, geladen via **Hugo Modules**
(zie `go.mod` en het `module.imports`-blok in `hugo.yaml`). De content staat in `content/`,
in het Nederlands.

## Lokaal draaien

    cd docs
    hugo server          # live-reload op http://localhost:1313
    hugo --gc --minify   # productiebuild (output in docs/public/, ge-gitignored)

## Een nieuwe docs-pagina toevoegen

1. Maak een Markdown-bestand in `content/docs/`, bijv. `content/docs/mijn-pagina.md`.
2. Geef het front matter met een titel en een `weight` (bepaalt de volgorde in de zijbalk):

       ---
       title: Mijn pagina
       weight: 8
       ---

       Tekst hier. Gebruik Hextra-shortcodes voor mooie opmaak:
       {{< callout type="info" >}}Een tip.{{< /callout >}}
       {{< cards >}}{{< card title="..." subtitle="..." >}}{{< /cards >}}

3. Wil je de pagina ook als kaart op de docs-landingspagina? Voeg een `{{< card >}}` toe in
   `content/docs/_index.md`.
4. Build lokaal (`hugo --gc --minify`) om te checken dat het schoon bouwt.

> **Afspraak:** werk de docs bij in dezelfde wijziging als de code. Nieuwe feature → nieuwe of
> bijgewerkte pagina, en zo nodig een regel in `content/docs/roadmap.md`.

## Handige Hextra-shortcodes

- `{{< callout type="info|warning" >}}...{{< /callout >}}` of `{{< callout emoji="🫙" >}}...{{< /callout >}}`
- `{{< cards >}} {{< card title="" subtitle="" icon="" link="" >}} {{< /cards >}}`
- Hero/feature-shortcodes op de landingspagina (`content/_index.md`).

Iconen zijn Heroicons-namen (bijv. `information-circle`, `cube`, `cloud`). Zie de
[Hextra-documentatie](https://imfing.github.io/hextra/) voor de volledige lijst.

## Thema bijwerken

    cd docs
    hugo mod get -u github.com/imfing/hextra   # naar de nieuwste versie
    hugo mod tidy

De module-cache (`~/go/pkg/mod` of `docs/_vendor/`) wordt **niet** gecommit; `go.mod`/`go.sum`
wel.
