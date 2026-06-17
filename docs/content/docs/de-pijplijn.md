---
title: De pijplijn
weight: 2
---

zeef is een pijplijn van **negen onafhankelijk draaibare, onafhankelijk gelogde stages**. Elke
stage leest en schrijft hetzelfde canonieke `Document`-object; scores en beslissingen stapelen
zich daarop op.

## Overzicht

| # | Stage | Wat het doet |
|---|-------|--------------|
| 1 | **Ingest** | Format-robuuste loaders (`.eml`/`.msg` met headers, digitale PDF). |
| 2 | **Normalize** | Naar één canoniek `Document`; tekst opschonen, metadata extraheren. |
| 3 | **Relate** | Mailthreads uit headers, near-duplicates (MinHash + cosine). |
| 4 | **Scope-filter** | Regels eerst, LLM alleen voor twijfelgevallen — elke uitsluiting met reden. |
| 5 | **Embed** | Chunks omzetten naar vectoren met de profiel-embedding-provider. |
| 6 | **Retrieve** | Eerste kandidatenpas t.o.v. de verfijnde zoekvraag (vector, optioneel BM25-hybride). |
| 7 | **Rerank** | Precisiepas met cross-encoder of LLM-reranker. |
| 8 | **Select** | Instelbare cutoff (`--top-n` / `--threshold` / `--target`), recall-gericht. |
| 9 | **Export** | `inventory.xlsx`, `relations.json`, `audit.jsonl`. |

## De stages in detail

### 1–2 · Ingest & normalize

Pluggable loaders achter een `Loader`-protocol lezen `.eml`/`.msg` (headers behouden) en digitale
PDF. Alles wordt genormaliseerd naar één canoniek `Document` — zie [Architectuur](../architectuur).
Eén `.eml` kan meerdere documenten opleveren (body + bijlagen).

### 3 · Relate

{{< cards >}}
  {{< card title="Mailthreads" icon="mail"
        subtitle="Opgebouwd uit RFC 5322-headers (Message-ID / In-Reply-To / References). Geen headers? Dan een expliciet als heuristiek gemarkeerde val-terug." >}}
  {{< card title="Near-duplicates" icon="duplicate"
        subtitle="MinHash/SimHash genereert kandidaten, bevestigd door embedding-cosine boven een drempel. Exacte duplicaten via de content-hash." >}}
{{< /cards >}}

Relaties worden vastgelegd als getypeerde `Relation`s met *evidence* (de headerwaarde, hash of
cosine die de relatie rechtvaardigt).

### 4 · Scope-filter

Een geordende lijst **deterministische regels** draait eerst: forwarded-only mail, agenda-uitnodigingen,
procesnotificaties, eerdere mails al vertegenwoordigd door een thread-head, duplicaten. Alleen
documenten die geen enkele regel beslist, gaan naar de LLM — en alleen in `cloud`/niet-`--no-llm`
runs.

{{< callout type="info" >}}
  Elke beslissing — regel of LLM — schrijft een leesbare `decision_reason` en een audit-event.
  Deterministische regels zijn per constructie auditbaar; de LLM is het duurdere, lastiger te
  verklaren pad en behandelt dus de minimale rest.
{{< /callout >}}

### 5–7 · Embed → Retrieve → Rerank

De kandidaten worden t.o.v. de verfijnde zoekvraag bepaald: eerst vector-retrieval (optioneel een
BM25-hybride), daarna een precisie-rerank met een cross-encoder of LLM-reranker. Welke providers
hier draaien, hangt af van het gekozen [profiel](../architectuur#profielen).

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

- **`inventory.xlsx`** — id, score, categorie, samenvatting, reden.
- **`relations.json`** — de relatiegraaf.
- **`audit.jsonl`** — de volledige [audit-trail](../audit-trail).
