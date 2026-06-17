---
title: Roadmap
weight: 6
---

De eerste werkende CLI-MVP (`converge-mvp`) dekt de volledige pijplijn van ingest tot export. Een
aantal capaciteiten is bewust **buiten scope** gehouden voor change #1 en staat gepland als
vervolg-change. De bron is `openspec/changes/` in de repo.

{{< callout type="info" >}}
  De volgorde hieronder is indicatief. De canonieke status leeft in de OpenSpec-changes in de
  repo, niet in deze pagina — werk beide bij wanneer een change van scope verandert.
{{< /callout >}}

## Gepland

{{< cards >}}
  {{< card title="OCR + VL-reranker" icon="photograph"
        subtitle="Een driver voor gescande PDF's (OCR) en een multimodale visual-language reranker, zodat ook beeld-zware documenten meekomen." >}}
  {{< card title="Enrich" icon="sparkles"
        subtitle="Clustering, samenvatting en highlighting — de selectie niet alleen kleiner, maar ook beter doorzoekbaar en uitlegbaar maken." >}}
  {{< card title="Web-UI" icon="desktop-computer"
        subtitle="Een interface bovenop de CLI om runs te starten, de selectie te beoordelen en de audit-trail interactief te doorlopen." >}}
  {{< card title="Connectoren" icon="link"
        subtitle="Koppelingen naar M365, DMS- en zaaksystemen, zodat zeef rechtstreeks op bronsystemen kan aansluiten in plaats van op een lokale map." >}}
{{< /cards >}}

## Buiten scope (blijvend)

- **Fase 1 — Zoeken in bronsystemen.** Dat is het werk vóór zeef.
- **Fase 3 — Lakken (redactie).** Dat is het werk ná zeef.

Zie [Wat is zeef](../wat-is-zeef#positionering) voor de fasering.
