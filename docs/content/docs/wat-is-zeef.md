---
title: Wat is zeef
weight: 1
---

`zeef` lost een pijnlijke tussenstap in het Woo-proces op.

## Het probleem

Nadat bronsystemen zijn doorzocht (fase 1), blijft een afdeling achter met **~1.000
semi-relevante documenten** die teruggebracht moeten worden tot een **kernrelevante selectie
(~100)** vóór het lakken (fase 3). Vandaag gebeurt die convergentie met de hand: traag,
inconsistent en lastig te verantwoorden.

{{< callout type="warning" >}}
  Er bestond geen open-source tool voor deze stap — terwijl het publicatie- en zoek-einde van de
  keten (OpenWoo / Common Ground) juist goed gedekt is. Dat gat vult zeef.
{{< /callout >}}

## De kernbelofte

{{< callout emoji="🫙" >}}
  **1.000 documenten erin, ~100 eruit** — instelbaar, recall-gericht, en volledig navolgbaar.
{{< /callout >}}

Elke selectie- en uitsluitbeslissing is achteraf reproduceerbaar en herleidbaar via een
append-only audit-trail. zeef bedenkt geen relevantie-ranking opnieuw, maar leent de
recall-gerichte aanpak van **e-discovery / TAR** (technology-assisted review): een relevant
document missen is erger dan ruis insluiten.

## Positionering

zeef is de ontbrekende open-source schakel **upstream** van de bestaande OpenWoo / Common Ground
publicatie- en zoekketen.

{{< cards >}}
  {{< card title="Fase 1 — Zoeken" subtitle="Bronsystemen doorzoeken. Buiten scope van zeef." >}}
  {{< card title="Fase 2 — Convergeren" subtitle="zeef: van ~1.000 naar ~100, navolgbaar." >}}
  {{< card title="Fase 3 — Lakken" subtitle="Redactie. Buiten scope van zeef." >}}
{{< /cards >}}

Downstream sluit zeef aan op OpenConnector, OpenRegister en OpenCatalogi — de bestaande Common
Ground publicatieketen.

## Engineeringfilosofie

> *Boring and auditable* boven snel of slim.

Niets dat niet in een ISO 27001-context uit te leggen is. Concreet betekent dat:

- **Deterministisch waar het kan.** Regels, hashes en headers gaan vóór modellen.
- **LLM alleen waar nodig** — en **altijd gelogd**, inclusief de exacte prompt.
- **Reproduceerbaar.** Een herhaalde run levert dezelfde document-ids op (content-adressering).
- **Herleidbaar.** Zowel de geselecteerde kern als de uitgesloten rest is te reconstrueren uit
  de audit-log.
