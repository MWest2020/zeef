---
status: draft
last_reviewed: 2026-07-12
---

# Aan de slag

zeef is een Python-project, beheerd met [`uv`](https://docs.astral.sh/uv/).

## Vereisten

> **Let op:** Python **3.12+** en `uv`. Gebruik nooit `pip` rechtstreeks — `uv`
> beheert de venv en de lockfile.

Het `sovereign`-profiel draait standaard volledig air-gapped op **deterministische lokale
providers** (feature-hashing-embedding + lexicale reranker) — geen modelgewichten of netwerk
nodig. Wil je modelgebaseerde soevereine drivers, dan staat Qwen3 via Ollama/vLLM achter dezelfde
interfaces klaar. Het `cloud`-profiel vereist egress naar de Claude API (en een sleutel uit de
omgeving).

## Installeren

```bash
uv sync                  # venv + lockfile, inclusief de dev-toolgroep (pytest, ruff)
uv run pytest            # tests (volledig offline)
uv run ruff check        # lint
uv run zeef --help       # CLI
```

## Je eerste convergentie

De kerncommando is `zeef converge`: het draait de volledige pijplijn over een lokale map.

```bash
zeef converge ./docs --query "..." --profile sovereign --target 100
```

### Veelgebruikte vlaggen

| Vlag | Betekenis |
|------|-----------|
| `--query "..."` | De verfijnde zoekvraag waartegen wordt geretrieved en gererankt. |
| `--profile sovereign\|cloud` | Kiest de driver-set. `sovereign` is lokaal/air-gapped, `cloud` gebruikt de Claude API. |
| `--target N` | Adaptieve selectie richting ~N documenten (toont de score-"knie"). |
| `--top-n N` | Exact N documenten. |
| `--threshold X` | Alles met eindscore ≥ X. |
| `--score-top-k N` | Aantal reranked kandidaten dat de LLM scoort (`0` = alle). |
| `--near-dup X` | Cosinus-drempel voor near-duplicates (default `0.9`; lager = agressiever samenvouwen). |
| `--no-llm` | Slaat alle generatieve stappen over — volledig deterministisch. |

## De resultaten

Een run schrijft naar een verse run-map:

- **`inventory.xlsx`** — de geselecteerde set: id, score, categorie, samenvatting, reden, motivatie.
- **`relations.json`** — de relatiegraaf (threads, duplicaten, bijlagen).
- **`criteria.json`** — de gearticuleerde relevantiecriteria — de inspecteerbare definitie.
- **`run-manifest.json`** — run-parameters en de vastgelegde per-stage runtimes.
- **`audit.jsonl`** — de volledige audit-log; zie [Audit-trail](../reference/audit-trail.md).

## Lokaal of in de cloud?

> **Tip:** begin met `--profile sovereign --no-llm` als je geen modellen klaar hebt staan: dat
> draait puur op embeddings + rerank en heeft geen netwerk of LLM nodig. Schakel naderhand over op
> een vol profiel zonder de pijplijn te wijzigen — zie
> [Architectuur → Profielen](../explanation/architectuur.md#profielen).
