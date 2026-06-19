---
title: De pijplijn
weight: 2
---

zeef is een pijplijn van **onafhankelijk draaibare, onafhankelijk gelogde stages**. Elke stage
leest en schrijft hetzelfde canonieke `Document`-object; scores en beslissingen stapelen zich
daarop op. De pijplijn heeft **twee LLM-momenten — een aan het begin en een aan het eind** — en
houdt de hele tussenliggende keten deterministisch.

## Overzicht

| # | Stage | Wat het doet | LLM? |
|---|-------|--------------|------|
| 1 | **Criteria** | Zet de zoekvraag om in een expliciete, benoemde set relevantiecriteria. | **LLM (begin)** |
| 2 | **Ingest & normalize** | Format-robuuste loaders (`.eml`/`.msg`, digitale PDF) → één canoniek `Document`. | nee |
| 3 | **Relate** | Mailthreads uit headers, near-duplicates (MinHash + cosine). | nee |
| 4 | **Scope-filter** | Regels eerst, LLM alleen voor twijfelgevallen — elke uitsluiting met reden. | regels + LLM-randgeval |
| 5 | **Embed → Retrieve** | Chunks → vectoren; eerste kandidatenpas t.o.v. de zoekvraag (optioneel BM25-hybride). | nee |
| 6 | **Rerank** | Deterministische precisiepas; bepaalt welke top-K naar de LLM-scoring gaat. | nee |
| 7 | **Score** | LLM scoort de top-K tegen de criteria: relevantiescore **én** motivatie per document. | **LLM (eind)** |
| 8 | **Select** | Instelbare cutoff (`--top-n` / `--threshold` / `--target`), recall-gericht. | nee |
| 9 | **Export** | `inventory.xlsx`, `relations.json`, `criteria.json`, `audit.jsonl`. | nee |

{{< callout type="info" >}}
  **De regel voor wel/niet LLM.** Een LLM komt er alleen aan te pas bij een oordeel onder
  taalkundige ambiguïteit zónder mechanische grondwaarheid, én waar een motivatie de
  verdedigbaarheid verhoogt — dus: criteria, grensgeval-scoring (en later categorisering en
  samenvatting). Alles met een mechanische grondwaarheid — threads, duplicaten, regel-uitsluiting,
  chunking, vector-/lexicale retrieval, de cutoff-rekensom — blijft deterministisch.
{{< /callout >}}

## De stages in detail

### 1 · Criteria (het begin)

Eén LLM-call vertaalt de verfijnde zoekvraag naar een korte set benoemde criteria (label +
omschrijving) — de geschreven relevantiedefinitie die een beoordelaar kan lezen *en betwisten*.
Ze worden gelogd mét de exacte prompt en weggeschreven als `criteria.json`. Onder `--no-llm`
valt de stage deterministisch terug op één criterium gelijk aan de ruwe zoekvraag, zodat de
pijplijn air-gapped blijft draaien.

### 2–3 · Ingest, normalize & relate

Pluggable loaders achter een `Loader`-protocol lezen `.eml`/`.msg` (headers behouden) en digitale
PDF; alles wordt genormaliseerd naar één `Document` (zie [Architectuur](../architectuur)). Eén
`.eml` kan meerdere documenten opleveren (body + bijlagen). Relate bouwt mailthreads uit
RFC 5322-headers en near-duplicates (MinHash/SimHash, bevestigd door embedding-cosine; exacte
duplicaten via de content-hash), vastgelegd als getypeerde `Relation`s met *evidence*. De
near-duplicate-drempel (de cosinus-grens waarboven twee documenten als bijna-dubbel gelden) is
instelbaar met `--near-dup` (default `0.9`): lager vouwt agressiever samen — met recall-risico op
thematisch-verwante maar onderscheiden documenten — hoger laat alleen vrijwel-identieke stukken
samenvallen. Stem af op de dataset.

### 4 · Scope-filter

Een geordende lijst **deterministische regels** draait eerst (forwarded-only, agenda-uitnodiging,
procesnotificatie, thread-tail, duplicaat). Alleen documenten die geen enkele regel beslist gaan
naar de LLM, en alleen in niet-`--no-llm` runs. Die LLM-stap is **recall-georiënteerd**: hij sluit
alléén uit wat met zekerheid buiten scope valt (`UITSLUITEN`) en behoudt twijfelgevallen — de
precisie-verfijning gebeurt later in de relevantiescoring. Elke beslissing — regel of LLM —
schrijft een leesbare `decision_reason` en een audit-event.

### 5–6 · Embed → Retrieve → Rerank (het deterministische midden)

De kandidaten worden t.o.v. de zoekvraag bepaald: eerst vector-retrieval (optioneel een
BM25-hybride), daarna een precisie-rerank met een cross-encoder of lexicale reranker. De rerank
is hier niet langer het eindoordeel: hij **ordent en trimt** de kandidaten tot een ruime top-K
die naar de LLM-scoring gaat. Welke providers hier draaien hangt af van het
[profiel](../architectuur#profielen).

### 7 · Score (het eind)

De LLM scoort elk van de top-K reranked documenten tegen de gearticuleerde criteria: een
relevantiescore (0–100 → `llm_relevance`) **plus** een motivatie van één zin (*"scoort hoog:
bevat publicatie- én geheimhoudingsclausule tussen de genoemde partijen"*). Die relevantiescore
wordt de `final`-score waarop de selectie beslist. Kandidaten buiten de top-K worden expliciet
gedemoveerd (gelogd, niet stil gedropt). `--score-top-k N` regelt de top-K (`0` = alle); onder
`--no-llm` slaat de stage over en blijft `final` de rerank-score — dan is de run volledig
deterministisch.

{{< callout type="info" >}}
  **Wat drijft de top-X?** Mét LLM: de `final`-score is de LLM-relevantiescore tegen de criteria,
  met een motivatie per document. Zónder LLM (`--no-llm`): de deterministische rerank-score. De
  cutoff zelf (stap 8) is in beide gevallen pure rekenkunde.
{{< /callout >}}

### 8 · Select

Drie expliciete, niet-magische cutoff-modi:

| Modus | Vlag | Gedrag |
|-------|------|--------|
| Hard aantal | `--top-n N` | Exact N documenten. |
| Drempel | `--threshold X` | Eindscore ≥ X. |
| Doelaantal | `--target N` | Adaptieve drempel richting ~N; toont de score-"knie" zodat je bewust kiest. |

Een instelbare **recall-bias** verbreedt de selectie bij gelijke of net-onder-de-drempel scores
richting insluiting. De gekozen modus en parameters worden gelogd.

### 9 · Export

zeef levert op:

- **`inventory.xlsx`** — id, score, categorie, samenvatting, reden, **motivatie**.
- **`relations.json`** — de relatiegraaf.
- **`criteria.json`** — de gearticuleerde relevantiecriteria (de inspecteerbare definitie).
- **`audit.jsonl`** — de volledige [audit-trail](../audit-trail).
