---
status: draft
last_reviewed: 2026-07-12
---

# Audit-trail

> 🔎 De audit-trail is **de differentiator** van zeef. Niet de selectie zelf, maar de volledige
> navolgbaarheid ervan.

## Waarom dit de kern is

De Woo draait om transparantie en verantwoording. Een selectie die je niet kunt uitleggen, is in
een ISO 27001-context waardeloos. zeef draait die eis om tot een ontwerpprincipe: **elke
selectie- én uitsluitbeslissing moet achteraf reproduceerbaar en herleidbaar zijn**.

Zowel de geselecteerde kern als de uitgesloten rest is volledig te reconstrueren uit de log.

## Hoe het werkt

De audit-trail is een **append-only JSONL-bestand**: één event per stage-actie. Er wordt
uitsluitend gestructureerd gelogd — geen ad-hoc prints.

Elk event bevat:

| Veld | Inhoud |
|------|--------|
| `timestamp` | Wanneer de actie plaatsvond. |
| `stage` | Welke stage de actie uitvoerde. |
| `document_id(s)` | Welke documenten het betrof. |
| `action` | Wat er gebeurde (query gedraaid, sub-selectie, uitsluiting, …). |
| `inputs` | Query, drempels en andere parameters. |
| `model` + `location` | Welk model, en **waar** het draaide: `local` of `cloud`. |
| `prompt` | Voor LLM-stappen: de **exacte** prompt. |

## Wat dit oplevert

- **Reproduceerbaar** — content-geadresseerde ids + gelogde parameters: een herhaalde run is verifieerbaar dezelfde.
- **Herleidbaar** — voor elk document is na te gaan waarom het is geselecteerd of uitgesloten.
- **Verklaarbaar** — LLM-stappen leggen hun exacte prompt en modelidentiteit vast — uit te leggen aan een auditor.

## Determinisme & LLM

LLM-nondeterminisme zou reproduceerbaarheid kunnen ondermijnen. Daarom:

- **Temperatuur 0** waar de provider dat toelaat.
- **Volledige prompt + model-id + locatie** gelogd voor elke generatieve stap.
- **`--no-llm`** geeft een volledig deterministische run — de maximaal-soevereine fallback.

> **Info:** de audit-log is de *source of truth* voor het transparantie-criterium. Hij wordt naast
> `inventory.xlsx` en `relations.json` geëxporteerd als `audit.jsonl`.
