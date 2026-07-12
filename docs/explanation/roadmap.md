---
status: draft
last_reviewed: 2026-07-12
---

# Roadmap

De eerste werkende CLI-MVP (`converge-mvp`) dekt de volledige pijplijn van ingest tot export.
Change #2 (`criteria-scoring`) is daar bovenop **geïmplementeerd**: criteria-articulatie aan het
begin en LLM-relevantiescoring met een motivatie per document aan het eind, met een deterministisch
midden. Een aantal capaciteiten is bewust **buiten scope** gehouden en staat gepland als
vervolg-change. De bron is `openspec/changes/` in de repo.

> **Info:** de volgorde hieronder is indicatief. De canonieke status leeft in de OpenSpec-changes in
> de repo, niet in deze pagina — werk beide bij wanneer een change van scope verandert.

## Gepland

- **OCR + VL-reranker** — een driver voor gescande PDF's (OCR) en een multimodale visual-language reranker, zodat ook beeld-zware documenten meekomen.
- **Enrich** — clustering, samenvatting en highlighting — de selectie niet alleen kleiner, maar ook beter doorzoekbaar en uitlegbaar maken.
- **Web-UI** — een interface bovenop de CLI om runs te starten, de selectie te beoordelen en de audit-trail interactief te doorlopen.
- **Connectoren** — koppelingen naar M365, DMS- en zaaksystemen, zodat zeef rechtstreeks op bronsystemen kan aansluiten in plaats van op een lokale map.

## Buiten scope (blijvend)

- **Fase 1 — Zoeken in bronsystemen.** Dat is het werk vóór zeef.
- **Fase 3 — Lakken (redactie).** Dat is het werk ná zeef.

Zie [Wat is zeef](wat-is-zeef.md#positionering) voor de fasering.
