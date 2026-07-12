---
status: draft
last_reviewed: 2026-07-12
---

# Bijdragen

zeef is open source onder de [EUPL-1.2](https://github.com/MWest2020/zeef/blob/main/LICENSE) —
aansluitend bij de Common Ground / Nederlandse-overheidscontext. Bijdragen zijn welkom.

## Voordat je begint

> **Info:** zeef werkt met **OpenSpec**: substantiële wijzigingen beginnen als een change in
> `openspec/changes/` (proposal, design, specs, tasks) vóór de code. Lees de change die je raakt
> eerst door.

## Ontwikkelomgeving

```bash
uv sync --extra dev      # venv + lockfile
uv run pytest            # tests
uv run zeef --help       # CLI
```

## Codeprincipes

Houd de [engineeringfilosofie](wat-is-zeef.md#engineeringfilosofie) aan:

- **Boring and auditable** — niets dat niet in een ISO 27001-context uit te leggen is. Deterministisch waar het kan; LLM alleen waar nodig en altijd gelogd.
- **Bestanden ≤ 200 regels** — splits langs natuurlijke naden: één bestand per loader, driver en stage. Meer bestanden, veel makkelijker te reviewen.
- **Gestructureerd loggen** — geen ad-hoc prints. Elke betekenisvolle actie schrijft een audit-event.

## Documentatie meeschrijven

Werk de docs bij in **dezelfde wijziging** als de code. Voegt een change een capaciteit toe of
verandert die de scope? Dan hoort de bijbehorende docs-pagina (en zo nodig de
[Roadmap](roadmap.md)) in diezelfde PR. De gearchiveerde Hugo-site en haar auteursgids staan onder
`site/` in de repo (`site/CONTENT.md`).

## Pull requests

- Vertrek vanaf een branch met een duidelijke prefix (`feat/`, `fix/`, `docs/`, …).
- Houd PR's klein en reviewbaar.
- Zorg dat `uv run pytest` slaagt vóór je een PR opent.
