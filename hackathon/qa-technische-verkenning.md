# Q&A — Technische Verkenning Woo (26 juni 2026)

> **Levend document.** Vragen die de *architectuur* bepalen vóór we ingestion- en modelkeuze
> bevriezen. Vul antwoorden in zodra ze binnenkomen; werk daarna de betrokken aannames en de
> presentatie bij.

**Prioriteit:** **[P1]** must-ask (verandert de architectuur) · **[P2]** belangrijk ·
**[P3]** nuttig, anders zelf aannemen en aanname expliciet maken.

**Status per vraag:** ⬜ open · 🟦 gesteld · ✅ beantwoord.

---

## A. Data & formaat — bepaalt de ingestion-laag (hoogste risico)

| # | P | Vraag | Status | Antwoord |
|---|---|-------|--------|----------|
| A1 | P1 | In welk formaat komen de ~1.000 documenten? Originele `.eml`/`.msg` of gerenderde/geprinte PDF? Gemengd? *(Bepaalt of threadreconstructie kan.)* | ⬜ | |
| A2 | P1 | Zijn e-mailheaders intact (`Message-ID`, `In-Reply-To`, `References`) of alleen de gerenderde body? *(Zonder headers is threading heuristiek i.p.v. feit.)* | ⬜ | |
| A3 | P1 | Zijn de PDF's digitaal (tekstlaag) of gescand (OCR nodig, evt. stempels/handtekeningen)? *(Bepaalt of we een OCR- of multimodale rerank-stap nodig hebben.)* | ⬜ | |
| A4 | P2 | Komt metadata als aparte index (CSV/JSON: bestandsnaam, datum, afzender, type, herkomstsysteem), of zit alles in de documenten zelf? | ⬜ | |
| A5 | P2 | Krijgen we (een deel van) de dataset of een representatieve sample vóór 26 juni, of pas op de dag? | ⬜ | |
| A6 | P3 | Wat is de grootterange? Zeer grote bestanden/bijlagen (spreadsheets, zips, presentaties) die apart moeten? | ⬜ | |
| A7 | P3 | Moeten dubbelingen door ons gedetecteerd worden (aanname: ja), of zijn ze al gemarkeerd? | ⬜ | |

## B. Query & relevantie — bepaalt rerank-prompt en cutoff

| # | P | Vraag | Status | Antwoord |
|---|---|-------|--------|----------|
| B1 | P1 | Hoe weegt "een relevant document missen" t.o.v. "ruis in de selectie"? *(Recall vs. precision; bij Woo telt recall normaal zwaar. Bepaalt de drempel.)* | ⬜ | |
| B2 | P1 | Wanneer en in welke vorm krijgen we de verfijnde zoekvraag — op de dag, één query of meerdere deelvragen, vrije tekst of gestructureerd (termen/periode/afzenders)? | ⬜ | |
| B3 | P2 | Is er een gold-standard / referentieselectie ("de huidige handmatige wijze") waartegen jullie vergelijken? Krijgen we die ter inzage of alleen de eindvergelijking? | ⬜ | |
| B4 | P2 | "Relevantiecriteria bewust niet vooraf gedefinieerd" — wordt het positief gewaardeerd als wij onze relevantie-interpretatie expliciet maken en verantwoorden, of moeten we raden? | ⬜ | |

## C. Output & oplevervorm

| # | P | Vraag | Status | Antwoord |
|---|---|-------|--------|----------|
| C1 | P1 | De top-100 — hard getal of richtgetal? Telt een *instelbare* drempel/aantal (top-10, top-100, score-drempel) positief, of verwarrend? | ⬜ | |
| C2 | P2 | In welk formaat opleveren: Excel-inventarislijst met scores, lijst van document-ID's, mapstructuur? Verplicht formaat of vrij? | ⬜ | |
| C3 | P2 | Moeten de "buiten reikwijdte"-documenten óók gecategoriseerd worden opgeleverd (mét reden van uitsluiting), of alleen de geselecteerde kern? | ⬜ | |

## D. Omgeving — bepaalt of beide modi op de dag kunnen draaien (kritiek)

| # | P | Vraag | Status | Antwoord |
|---|---|-------|--------|----------|
| D1 | P1 | Mag data de zaal verlaten naar een externe cloud-API (LLM-API), of is de omgeving air-gapped / zonder egress? *(Bepaalt of cloud-modus live demonstreerbaar is.)* | ⬜ | |
| D2 | P1 | Mogen we eigen hardware meenemen en daar lokaal een model op draaien (de spelregels noemen "eigen randapparatuur zoals servers")? Incl. stroom/ruimte voor een GPU-machine? | ⬜ | |
| D3 | P3 | Is er wifi/bandbreedte van betekenis, of moeten we volledig zelfvoorzienend zijn? | ⬜ | |

## E. Beoordeling & vervolg

| # | P | Vraag | Status | Antwoord |
|---|---|-------|--------|----------|
| E1 | P2 | Wordt open source en digitale soevereiniteit expliciet (positief) meegewogen, of zijn dat puur informatieve velden? | ⬜ | |
| E2 | P3 | Het aanvullende format mag tot 3 juli — weegt dat even zwaar als de selectiekwaliteit op de dag, of is de dag dominant? | ⬜ | |

---

## Aannames bij uitblijven van antwoord (expliciet maken in de pitch)

Deze aannames sturen de architectuur en zijn bewust gekozen aan de veilige/soevereine kant.
Werk ze bij zodra het bijbehorende antwoord binnen is.

- **Formaat = gemengd** (`.eml` + PDF, deels gescand) → robuuste multi-format ingestion.
  *(koppelt aan A1–A3; design Open Q1/Q2)*
- **Recall weegt zwaarder dan precision** → conservatieve cutoff, liever iets te veel dan iets
  missen. *(koppelt aan B1; design Open Q4 / spec `select` recall-bias)*
- **Air-gapped mogelijk** → de soevereine (lokale Qwen) modus is de primaire demo, cloud is
  benchmark. *(koppelt aan D1; spec `provider-profiles`)*
- **Top-100 is richtgetal** → instelbare `--target` met adaptieve drempel die de score-knik
  toont. *(koppelt aan C1; spec `select`)*

## Koppeling naar de specificatie

De [P1]-vragen hierboven komen terug als **Open Questions** in
`openspec/changes/converge-mvp/design.md` (Q1–Q4). Houd beide in sync: een beantwoorde [P1]-vraag
hier hoort de bijbehorende Open Question in het design te sluiten.
