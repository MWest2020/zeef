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
| 3 | **Relate** | Mailthreads uit headers, near-duplicates (MinHash + cosine); partiële overlap als `overlaps-with`. | nee |
| 4 | **Scope-filter** | Regels eerst, LLM alleen voor twijfelgevallen — elke uitsluiting met reden. | regels + LLM-randgeval |
| 5 | **Embed → Retrieve** | Chunks → vectoren; eerste kandidatenpas t.o.v. de zoekvraag (optioneel BM25-hybride). | nee |
| 6 | **Rerank** | Deterministische precisiepas; bepaalt welke top-K naar de LLM-scoring gaat. | nee |
| 7 | **Score** | LLM scoort de top-K tegen de criteria: relevantiescore **én** motivatie per document. | **LLM (eind)** |
| 8 | **Select** | Instelbare cutoff (`--top-n` / `--threshold` / `--target`), recall-gericht. | nee |
| 9 | **Topics** | Deterministische clustering van de kern → onderwerp/deelonderwerp-menu; LLM labelt alleen (TF-IDF-fallback onder `--no-llm`). | label-only |
| 10 | **Summarise** | Per geselecteerd document een ≤100-woord inhoudssamenvatting; onder `--no-llm` overgeslagen (de `summary`-kolom vervalt dan). | **LLM** |
| 11 | **Export** | `inventory.xlsx`, `relations.json`, `criteria.json`, `topics.json`, `excluded.json`, `report.html`, `run-manifest.json`, `audit.jsonl`. | nee |

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

- **`inventory.xlsx`** — id, score, **categorie** (= onderwerp/deelonderwerp), **doc_type** (bestandstype, eigen kolom), **samenvatting** (≤100 woorden — alleen mét LLM; onder `--no-llm` vervalt de kolom), reden, **motivatie**. Samenvatting (wát het document zegt) staat los van motivatie (waaróm het scoort). De samenvatting vat de **opening** van het document samen (de eerste ~2000 tekens), niet het volledige document.
- **`relations.json`** — de relatiegraaf, inclusief `overlaps-with` voor partiële tekstoverlap (cosine in `[overlap_threshold, near_dup_threshold)`).
- **`criteria.json`** — de gearticuleerde relevantiecriteria (de inspecteerbare definitie).
- **`topics.json`** — het onderwerp → deelonderwerp → document-ids menu (het keuzemenu voor de verzoeker), met labels.
- **`excluded.json`** — de volledige uitgesloten set met redenen, machine-leesbaar; validity-uitsluitingen (`validity:*`) onderscheiden van semantische out-of-scope. Maakt "zowel de 100 als de rest" controleerbaar.
- **`report.html`** — een **self-contained, offline** rapport: de kern als inklapbaar onderwerp/deelonderwerp-menu én de uitgesloten rest per reden, met per document score/motivatie/samenvatting/reden/relaties en de gelakt-status. System fonts, vanilla JS, géén netwerk — de run-data staat inline; opent met `file://`. Onvertrouwde tekst wordt bij het renderen geëscaped.
- **`run-manifest.json`** — run-parameters (zoekvraag, providers/model, cutoff, clusterdrempels) en de vastgelegde per-stage runtimes.
- **`audit.jsonl`** — de volledige [audit-trail](../audit-trail).

Het **canonieke onderwerp-veld** is `Document.topic`/`subtopic` — gespiegeld in de inventory-kolom
`categorie` en in `topics.json`. Een document met chunks in meerdere clusters wordt via
**meerderheid** aan precies één onderwerp/deelonderwerp toegewezen (deterministische tie-break op de
medoid-chunk; zie design T7). Lees die velden, niet de ruwe chunk-clusters.
