---
status: draft
last_reviewed: 2026-07-12
---

# zeef — documentatie

`zeef` is de open-source convergentietool voor de Woo: het brengt een grote set
semi-relevante documenten (~1.000) terug naar een kernrelevante, instelbare selectie
(~100), met een volledige, herleidbare audit-trail. Dit is **fase 2** van het
Woo-proces (convergentie); het doorzoeken van bronsystemen (fase 1) en het lakken
(fase 3) vallen buiten scope.

> **Status:** deze documentatie is bij de migratie naar het handbook-docs-contract
> op `draft` gezet. Pagina's krijgen `status: current` zodra ze inhoudelijk zijn
> gereviewd. Voor een projectoverzicht: zie de [README](../README.md) in de repo-root.

## Secties

- **[how-to/](how-to/)** — taakgericht.
  - [Aan de slag](how-to/aan-de-slag.md) — installeren met `uv` en je eerste `zeef converge`.
- **[reference/](reference/)** — feiten (pijplijn, schema's, stages).
  - [De pijplijn](reference/de-pijplijn.md) — de stages van ingest tot export.
  - [Audit-trail](reference/audit-trail.md) — het append-only JSONL-logformaat.
  - [Scope-filter](reference/scope-filter.md) — de scope-filter-stage in detail.
- **[explanation/](explanation/)** — waarom-besluiten en achtergrond.
  - [Wat is zeef](explanation/wat-is-zeef.md) — het probleem, de positionering en de filosofie.
  - [Architectuur](explanation/architectuur.md) — het Document-model, Protocols en profielen.
  - [Roadmap](explanation/roadmap.md) — wat na de eerste CLI-MVP komt.
  - [Bijdragen](explanation/bijdragen.md) — ontwikkelomgeving en werkwijze.

De volledige, gerenderde Hugo-site staat gearchiveerd onder [`../site/`](../site/)
(pending definitieve verwijdering door Mark).
