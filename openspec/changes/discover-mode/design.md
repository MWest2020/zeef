## Context

De clustering (`cluster_topics`) en samenvatting (`summarise`) bestaan al, maar draaien op de
query-gedreven `selected`. Blinde ontdekking vraagt dezelfde operaties op het volledige,
ongefilterde corpus, vóór enige query. Doel: hergebruik, geen tweede implementatie.

## Goals

- Ontdek de onderwerp-landkaart van een ongezien corpus zonder dat de gebruiker een query levert.
- Hergebruik `cluster_topics` + labeling 1-op-1; geen parallelle clustering.
- Deterministisch en navolgbaar (zelfde audit-/runmap-discipline als `converge`).
- Begrensde looptijd op honderden documenten; LLM raakt labels + per-cluster samenvatting, niet elk document.

## Decisions

### D1: Discover = converge zonder de query-as
`run_discover` draait `ingest` → `validity` → `relate` (dedup) → embeddings → `cluster_topics`,
en slaat `criteria`/`retrieve`/`rerank`/`score`/`select` over — die zijn allemaal query-gedreven en
hebben hier geen betekenis. De clustering krijgt het volledige valide, gededupliceerde corpus mee
in plaats van `selected`. `cluster_topics` muteert nu over het hele corpus i.p.v. de selectie; de
functie zelf hoeft niet te wijzigen (ze neemt een lijst `Document` aan).

### D2: Embeddings vóór clustering, net als in converge
`cluster_topics` verwacht chunk-embeddings (uit retrieve) en herembedt anders deterministisch. In
de discover-route is er geen `retrieve`-stage, dus de chunks moeten geëmbed zijn vóór de clustering.
De bestaande `_chunk_vectors`-fallback (herembedt wanneer embeddings ontbreken) dekt dit al; voor
een groot corpus is een expliciete embed-stap vooraf efficiënter dan per-document lazy herembedden.
Welk van de twee: laat de implementatie de goedkoopste kiezen, mits het resultaat identiek en
deterministisch is.

### D3: Samenvatten op cluster-representanten, niet op elk document
`summarise` draait nu per geselecteerd document. Over een heel corpus van honderden documenten zou
dat te duur en te traag zijn (één LLM-call per document). Voor de ontdekking is een samenvatting
*per cluster* (op de medoid + naaste leden, die `cluster_topics` al medoid-eerst aanlevert) genoeg
om te tonen "waar gaat deze groep over". Dus: een dunne samenvattingsvariant die op de
cluster-representanten draait, niet op alle documenten. Onder `--no-llm` vervalt de samenvatting
(zoals `summarise` nu al doet) en blijven de TF-IDF-labels over.

### D4: Geen min_cluster_size-collapse die alles in "Overig" gooit
Op de 13-document-test stortte de clustering in tot één "Overig"-bucket omdat er te weinig
documenten waren. Op een corpus van honderden is dat geen probleem, maar de `min_cluster_size`
moet voor discover bewust gekozen worden (niet de converge-default die op een kleine selectie mikt),
zodat de landkaart betekenisvolle groepen toont i.p.v. veel ruis of één grote restbak. Maak het een
parameter met een discover-passende default; leg de gekozen waarde in het manifest.

### D5: Zelfde runmap- en report-structuur als converge
Output gaat naar een runmap met de ontdekte structuur als JSON (onderwerpen → deelonderwerpen →
doc_ids + labels + samenvattingen), plus `audit.jsonl`, plus een `report/`-viewer. Dat houdt
discover navolgbaar en demonstreerbaar, en laat de demo-UI er rechtstreeks op draaien zonder live
de pijplijn te starten.

## Risks

- **Clusterkwaliteit hangt aan de embeddings.** Met de sovereign-default (HashingEmbed, bag-of-words)
  is de clustering lexicaal van aard; met Ollama-embeddings semantisch. Voor een geloofwaardige
  ontdekking wil je waarschijnlijk semantische embeddings (`ZEEF_SOVEREIGN_EMBED=ollama`) — benoem
  dit, want de landkaart-kwaliteit staat of valt ermee.
- **Knip-hoogtes (`onderwerp_distance`/`deelonderwerp_distance`)** zijn nu op converge-selecties
  afgestemd. Op een vol corpus kunnen ze te grof of te fijn knippen; mogelijk discover-eigen defaults
  nodig. Parameter houden, waarde loggen.
- **O(n²)-clustering** over alle chunks van honderden documenten: begrensd via `max_chunks_per_doc`,
  maar houd de looptijd in de gaten en cap desnoods strenger voor discover.
