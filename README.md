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

| # | Stage | Wat |
|---|-------|-----|
| 1 | **Ingest** | Format-robuuste loaders (`.eml`/`.msg` met headers, digitale PDF) |
| 2 | **Normalize** | Naar één canoniek `Document`; tekst opschonen, metadata extraheren |
| 3 | **Relate** | Mailthreads uit headers, near-duplicates (MinHash + cosine) |
| 4 | **Scope-filter** | Regels eerst, LLM alleen voor twijfelgevallen — elke uitsluiting met reden |
| 5–7 | **Embed → Retrieve → Rerank** | Kandidaten t.o.v. de zoekvraag, dan een precisiepas |
| 8 | **Select** | Instelbare cutoff (`--top-n` / `--threshold` / `--target`), recall-gericht |
| 9 | **Export** | `inventory.xlsx`, `relations.json`, `audit.jsonl` |

Clustering, samenvatting/highlighting (enrich), OCR + VL-reranker en een web-UI zijn geplande
vervolgstappen — zie `openspec/changes/`.

## Twee modi

Eén pijplijn, alleen de drivers verschillen — geselecteerd met `--profile`:

- **`sovereign`** — volledig lokaal en air-gapped (Qwen3 via Ollama/vLLM, lokale embeddings +
  reranker). Geen netwerk. De primaire, soevereine demo.
- **`cloud`** — topmodel voor maximale kwaliteit (Claude API + hosted embeddings/rerank). Vereist
  egress; alleen waar de omgeving dat toestaat.

`--no-llm` slaat alle generatieve stappen over en selecteert puur op embedding + rerank — de
maximaal-soevereine, air-gapped-veilige fallback.

## Gebruik

```
zeef converge ./docs --query "..." --profile sovereign --target 100
```

Levert op: de geselecteerde set, `inventory.xlsx` (id, score, categorie, samenvatting, reden),
`relations.json` (relatiegraaf) en `audit.jsonl` (volledige audit-log).

## Status

Vroege fase. De specificatie van de eerste werkende CLI-MVP staat in
`openspec/changes/converge-mvp/` (proposal, design, specs, tasks) en is gevalideerd. De
codebasis bevat het canonieke datamodel, de protocols en het CLI-skelet; de stages worden
geïmplementeerd volgens `tasks.md`.

## Ontwikkelen

Vereist Python 3.12+ en [`uv`](https://docs.astral.sh/uv/) (nooit `pip` direct).

```
uv sync --extra dev      # venv + lockfile
uv run pytest            # tests
uv run zeef --help       # CLI
```

## Licentie

[EUPL-1.2](LICENSE) — aansluitend bij de Common Ground / Nederlandse-overheidscontext.
