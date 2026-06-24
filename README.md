# zeef

**Open-source convergentietool voor de Woo.** `zeef` brengt een grote set semi-relevante
documenten (~1.000) terug naar een kernrelevante selectie (~100, instelbaar) — mét volledige
navolgbaarheid. Dit is **fase 2** van het Woo-proces: het doorzoeken van bronsystemen (fase 1)
en het lakken (fase 3) vallen buiten scope.

> Werknaam *zeef*: 1.000 documenten erin, ~100 eruit.

## Positionering

`zeef` is de ontbrekende open-source schakel **upstream** van de bestaande OpenWoo / Common
Ground publicatie- en zoekketen (OpenConnector / OpenRegister / OpenCatalogi). Het methodische
vakgebied is **e-discovery / TAR** (technology-assisted review): we lenen daar de recall-gerichte
aanpak van in plaats van relevantie-ranking opnieuw uit te vinden.

## Engineeringfilosofie

> *Boring and auditable* boven snel of slim.

Niets dat niet in een ISO 27001-context uit te leggen is. Deterministisch waar het kan; LLM
alleen waar nodig en **altijd gelogd**. Elke selectie- en uitsluitbeslissing is achteraf
reproduceerbaar en herleidbaar via een append-only audit-trail.

## De pijplijn

| # | Stage | Wat | LLM? |
|---|-------|-----|------|
| 1 | **Criteria** | Zoekvraag → expliciete, benoemde relevantiecriteria (`criteria.json`) | **LLM (begin)** |
| 2 | **Ingest & normalize** | Format-robuuste loaders (`.eml`/`.msg`, digitale PDF) → canoniek `Document`, mét extractie-gezondheid (`char_count`/`parse_ok`/`redaction_ratio`) | nee |
| 3 | **Validity-gate** | Deterministische pre-flight: sluit mechanisch-onbruikbare documenten uit (onleesbaar, leeg-na-OCR) met `validity:`-reden; behoudt gelakt-maar-leesbare | nee |
| 4 | **Relate** | Mailthreads uit headers, near-duplicates (MinHash + cosine); partiële overlap als `overlaps-with` | nee |
| 5 | **Scope-filter** | Regels eerst, LLM alleen voor twijfelgevallen — elke uitsluiting met reden | regels + LLM-randgeval |
| 6–7 | **Embed → Retrieve → Rerank** | Kandidaten t.o.v. de zoekvraag; rerank trimt tot de top-K | nee |
| 8 | **Score** | LLM scoort de top-K tegen de criteria: relevantiescore + motivatie per document | **LLM (eind)** |
| 9 | **Select** | Instelbare cutoff (`--top-n` / `--threshold` / `--target`), recall-gericht | nee |
| 10 | **Topics** | Deterministische clustering → onderwerp/deelonderwerp-menu; LLM labelt alleen | label-only |
| 11 | **Summarise** | Per geselecteerd document een ≤100-woord inhoudssamenvatting; onder `--no-llm` overgeslagen (kolom afwezig) | **LLM** |
| 12 | **Export** | `inventory.xlsx`, `relations.json`, `criteria.json`, `topics.json`, `excluded.json`, `report.html`, `run-manifest.json`, `audit.jsonl` | nee |

**Twee LLM-momenten, de rest deterministisch.** De regel: LLM alleen bij een oordeel onder
taalkundige ambiguïteit zónder mechanische grondwaarheid, én waar een motivatie de
verdedigbaarheid verhoogt. Clustering, samenvatting/highlighting (enrich), OCR + VL-reranker en
een web-UI zijn geplande vervolgstappen — zie `openspec/changes/`.

## Twee modi

Eén pijplijn, alleen de drivers verschillen — geselecteerd met `--profile`:

- **`sovereign`** — volledig lokaal en air-gapped. De MVP-default gebruikt **deterministische
  lokale providers** (een feature-hashing-embedding + een lexicale BM25-reranker): geen netwerk,
  geen modelgewichten, volledig reproduceerbaar. De modelgebaseerde soevereine drivers (Qwen3 via
  Ollama/vLLM) staan achter dezelfde interfaces en zijn te kiezen zodra gewichten klaarstaan.
- **`cloud`** — topmodel voor maximale kwaliteit (Claude API + hosted embeddings/rerank). Vereist
  egress; constructie kan zonder sleutel, maar elke echte call is gated op een API-sleutel uit de
  omgeving.

De Claude-LLM kent twee authenticatie-modi. Standaard een **API-sleutel** (`ANTHROPIC_API_KEY`,
pay-per-token). Met `--subscription` draait de LLM via je **Claude-abonnement** (OAuth, eenmalig
`ant auth login`); dat impliceert de cloud-LLM maar laat embeddings/rerank van het gekozen profiel
staan — bv. lokale Ollama-embeddings + Claude-LLM. In abonnement-modus wordt een eventuele
`ANTHROPIC_API_KEY` uit de omgeving verwijderd, zodat die nooit per ongeluk credits verbruikt.

> **Billing-kanttekening:** afhankelijk van je Claude-account kan de OAuth-credential alsnog uit
> hetzelfde **API-credit-saldo** trekken in plaats van uit een vast plan (waargenomen: een run die
> faalt met *"credit balance is too low to access the Anthropic API"*). De abonnement-modus is dan
> wél correct geauthenticeerd, maar zonder credit-saldo draait er niets. Controleer *Plans & Billing*.

`--no-llm` slaat alle generatieve stappen over: criteria valt terug op de ruwe zoekvraag en de
selectie loopt puur op embedding + rerank — de maximaal-soevereine, air-gapped-veilige modus die
de acceptatietest gebruikt.

## Gebruik

```
zeef converge ./docs --query "..." --profile sovereign --target 100
```

Volledig air-gapped, zonder LLM of netwerk:

```
zeef converge ./docs --query "..." --profile sovereign --no-llm --target 100
```

`--score-top-k N` begrenst hoeveel reranked kandidaten de LLM-scoring beoordeelt (`0` = alle).

Levert op (in een verse run-map per aanroep): de geselecteerde set, `inventory.xlsx` (id, score,
categorie = onderwerp/deelonderwerp, doc_type, samenvatting — alleen mét LLM, anders weggelaten —,
reden, **motivatie**), `relations.json` (relatiegraaf incl. `overlaps-with` voor partiële overlap),
`criteria.json` (de gearticuleerde relevantiecriteria),
`topics.json` (het onderwerp/deelonderwerp-keuzemenu voor de verzoeker),
`excluded.json` (de volledige uitgesloten set + redenen, validity vs semantisch),
`report.html` (een **self-contained, offline** rapport — kern als inklapbaar menu én de uitgesloten
rest, opent met `file://` zonder server of netwerk),
`run-manifest.json` (run-parameters + per-stage runtimes) en `audit.jsonl` (volledige audit-log).

## Status

Eerste werkende CLI-MVP (`converge-mvp`) **geïmplementeerd en getest**. De volledige pijplijn
draait air-gapped: ingest (`.eml`/`.msg`, digitale PDF) → validity-gate (mechanisch-onbruikbaar
eruit, gelakt behouden) → relate (mailthreads + duplicaten) → scope-filter (regels eerst,
LLM-fallback) → embed/retrieve/rerank → select → export. De
specificatie staat in `openspec/changes/converge-mvp/` (proposal, design, 10 capability-specs,
tasks).

Change #2 (`criteria-scoring`) voegt de twee LLM-momenten met motivatie toe — criteria-articulatie
aan het begin en relevantiescoring (met een motivatie per document) aan het eind — terwijl het
midden deterministisch blijft. Onder `--no-llm` blijft het gedrag van change #1 exact behouden.
De spec staat in `openspec/changes/criteria-scoring/`. Geplande vervolgstappen (OCR/VL-reranker,
enrich, web-UI, connectoren, lakken) staan in dezelfde map.

## Ontwikkelen

Vereist Python 3.12+ en [`uv`](https://docs.astral.sh/uv/) (nooit `pip` direct).

```
uv sync                  # venv + lockfile, inclusief de dev-toolgroep (pytest, ruff)
uv run pytest            # tests (volledig offline)
uv run ruff check        # lint
uv run zeef --help       # CLI
```

Het `doc_id`-contract (content-geadresseerde id) leeft in het afhankelijkheidsvrije
`src/zeef/ids.py`, zodat een los repo (`zeef-eval`) het kan importeren zonder de pijplijn.

## Licentie

[EUPL-1.2](LICENSE) — aansluitend bij de Common Ground / Nederlandse-overheidscontext.
