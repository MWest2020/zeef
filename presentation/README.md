# zeef — presentatie

HTML-presentatie (Nederlands) voor `zeef`, gebouwd op een **lokaal gevendorde**
[reveal.js](https://revealjs.com) 5.1.0. Werkt volledig **offline / air-gapped**:
geen runtime-CDN, geen webfonts, geen externe netwerk-afhankelijkheden.

## Openen

Open simpelweg het bestand in een browser — geen server, geen build nodig:

- Dubbelklik `index.html`, of
- `xdg-open index.html` (Linux) / `open index.html` (macOS).

Navigatie: pijltjestoetsen of de controls rechtsonder. `F` = fullscreen,
`Esc` = overzicht, `S` = speaker-notes (indien toegevoegd).

## Bestanden

| Bestand | Wat |
|---|---|
| `index.html` | De deck zelf; slides staan in `<section>`-blokken |
| `theme.css` | Eigen kleur-/typografiethema (geladen ná reveal.css) |
| `reveal/` | Gevendorde reveal.js 5.1.0 dist (MIT): `reveal.js`, `reveal.css`, `reset.css`, `theme-white.css` |
| `README.md` | Dit bestand |

> `reveal/theme-white.css` wordt niet gebruikt (we hebben een eigen `theme.css`),
> maar is meegeleverd als fallback-thema.

## Een slide toevoegen of aanpassen

Elke slide is een `<section>` in `index.html`, voorafgegaan door een
gemarkeerde comment zodat slides makkelijk te vinden en te herordenen zijn:

```html
<!-- ============================================================ -->
<!-- SLIDE: <korte titel>                                          -->
<!-- ============================================================ -->
<section class="z-fill" data-background-color="#0d1b2a">
  <div class="z-kicker">Bovenschrift</div>
  <h2>Groot kernidee.</h2>
  <p class="z-lead">Korte krachtige toelichting.</p>
</section>
```

Plak een nieuw `<section>`-blok op de gewenste positie tussen de bestaande
`<!-- SLIDE: ... -->`-blokken. De volgorde in de HTML = de volgorde in de deck.

**Filosofie van de deck:** minimale bullets, één kernidee per slide,
beeld boven opsomming.

### Beschikbare hulpklassen (in `theme.css`)

- `z-fill` — centreert de slide-inhoud verticaal
- `z-center` — centreert tekst
- `z-kicker` — klein mono-bovenschrift in accentkleur
- `z-lead` — gedempte introtekst
- `z-big` — groot statement
- `z-accent` / `z-amber` / `z-mute` — tekstkleuren
- `z-card` — paneel met rand
- `z-cols` — flex-rij van gelijke kolommen
- `z-funnel` — de 1.000 → 100-funnel
- `z-pipe` + `.stage` (`.llm` / `.out`) — pijplijn-flow
- `z-jsonl` (`.k`/`.s`/`.v`) — audit-trail-codeblok
- `z-stat` (`.v`/`.l`) — groot statistiekgetal
- `z-mode` (`.sov`/`.cloud`) — modus-vergelijkingskaart

Kleuren staan als CSS-variabelen bovenin `theme.css` (`--z-bg`, `--z-accent`, …);
pas ze daar centraal aan.

## reveal.js opnieuw vendoren

Mocht `reveal/` ontbreken, haal de dist-bestanden opnieuw op (vereist netwerk
op de bouwmachine; de gebruikte demo-machine heeft het daarna niet meer nodig):

```
curl -sL -o reveal/reveal.js   https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js
curl -sL -o reveal/reveal.css  https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.css
curl -sL -o reveal/reset.css   https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reset.css
```

## Externe runtime-afhankelijkheden

**Geen.** Alle CSS/JS staat lokaal in `presentation/`. De deck is geverifieerd
vrij van `http(s)://`-asset-verwijzingen in de HTML.
