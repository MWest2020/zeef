---
title: Bijdragen
weight: 7
---

zeef is open source onder de [EUPL-1.2](https://github.com/MWest2020/zeef/blob/main/LICENSE) —
aansluitend bij de Common Ground / Nederlandse-overheidscontext. Bijdragen zijn welkom.

## Voordat je begint

{{< callout type="info" >}}
  zeef werkt met **OpenSpec**: substantiële wijzigingen beginnen als een change in
  `openspec/changes/` (proposal, design, specs, tasks) vóór de code. Lees de change die je raakt
  eerst door.
{{< /callout >}}

## Ontwikkelomgeving

```bash
uv sync --extra dev      # venv + lockfile
uv run pytest            # tests
uv run zeef --help       # CLI
```

## Codeprincipes

Houd de [engineeringfilosofie](wat-is-zeef#engineeringfilosofie) aan:

{{< cards >}}
  {{< card title="Boring and auditable" icon="shield-check"
        subtitle="Niets dat niet in een ISO 27001-context uit te leggen is. Deterministisch waar het kan; LLM alleen waar nodig en altijd gelogd." >}}
  {{< card title="Bestanden ≤ 200 regels" icon="scissors"
        subtitle="Splits langs natuurlijke naden: één bestand per loader, driver en stage. Meer bestanden, veel makkelijker te reviewen." >}}
  {{< card title="Gestructureerd loggen" icon="document-text"
        subtitle="Geen ad-hoc prints. Elke betekenisvolle actie schrijft een audit-event." >}}
{{< /cards >}}

## Documentatie meeschrijven

Werk de docs bij in **dezelfde wijziging** als de code. Voegt een change een capaciteit toe of
verandert die de scope? Dan hoort de bijbehorende docs-pagina (en zo nodig de
[Roadmap](roadmap)) in diezelfde PR. Hoe je een pagina toevoegt staat in `docs/CONTENT.md` in de
repo.

## Pull requests

- Vertrek vanaf een branch met een duidelijke prefix (`feat/`, `fix/`, `docs/`, …).
- Houd PR's klein en reviewbaar.
- Zorg dat `uv run pytest` slaagt vóór je een PR opent.
