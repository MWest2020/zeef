## Why

zeef's hele pijplijn hangt aan een query: de eerste stage `articulate_criteria(query, ...)` leidt
de criteria af, en alles daarna (retrieve → rerank → score → select) filtert het corpus tégen die
criteria. Er is geen modus die een ongeziene berg documenten inneemt en terúggeeft wat erin zit.

Dat is precies de kern van de beoogde use-case: de tool doorziet de documenten, vat ze samen en
biedt de ontdekte onderwerpen aan, wáárna de gebruiker kiest wat hij wil lezen. De ontdekking komt
vóór de facet-selectie, niet andersom. Zonder die stap moet de gebruiker de onderwerpen al kennen
om ze in te kunnen typen — een kip-ei dat de tool juist hoort weg te nemen.

De bouwstenen bestaan al en hoeven niet opnieuw gebouwd te worden: `cluster_topics` doet
tweelaags agglomeratieve clustering (onderwerp/deelonderwerp) met LLM- of TF-IDF-labels, en
`summarise` levert per-document samenvattingen. Het enige probleem is dat beide vandaag op de
query-gedreven `selected` draaien. Deze change ontkoppelt die clustering van de selectie en geeft
er een eigen entree voor: clusteren over het hele, ongefilterde corpus, vóór er een query is. Geen
parallelle implementatie — dezelfde stages, een andere orkestratie.

## What Changes

- **ADDED** `discover` — een capability die over het volledige corpus de onderwerp-landkaart
  oplevert zónder query: `ingest` → `validity` → `relate` (dedup) → embeddings → `cluster_topics`
  → per-cluster representatieve samenvatting. Resultaat: de genestte onderwerp/deelonderwerp-
  structuur met per cluster een label, een omvang, en een samenvatting van de kern.
- **ADDED** `cli` — een `zeef discover <docs>`-commando dat de discover-capability draait en de
  ontdekte landkaart in een runmap logt (zelfde uitvoerstructuur als `converge`: JSON/CSV +
  `audit.jsonl` + een `report/`-viewer), zodat de uitkomst navolgbaar en demonstreerbaar is.
- De clustering- en labelmachinerie (`cluster_topics`, `label_cluster`) wordt **hergebruikt**, niet
  gedupliceerd; waar die nu `selected` aanneemt, neemt de discover-route de volledige
  (gededupliceerde, valide) documentenset.

**Bewust uit scope** (latere change): de tweede trap — de gebruiker kiest een ontdekt onderwerp en
krijgt daar een top-n op. Dat is gewoon de bestaande `converge` met dat onderwerp als query, en
hoeft niet in deze change. Deze change levert uitsluitend de ontdekking (trap één).

## Capabilities

### New Capabilities
- `discover`: lever over het volledige corpus, zonder query, de genestte onderwerp/deelonderwerp-landkaart met per-cluster label, omvang en samenvatting — door de bestaande clustering- en samenvattingsstages op het ongefilterde corpus te draaien.

### Modified Capabilities
- `cli`: een nieuw `discover`-commando naast `converge`, met dezelfde runmap-/report-uitvoer.

## Impact

- **Code**: `src/zeef/pipeline/run.py` (een `run_discover`-orkestratie naast `run_converge`),
  `src/zeef/cli.py` (het `discover`-commando). `cluster_topics`/`summarise` worden hergebruikt;
  `summarise` krijgt mogelijk een dunne aanroep-variant die op cluster-representanten draait i.p.v.
  de selectie (zie design). Geen nieuwe dependencies.
- **Geen breuk** met `converge`: bestaande flow ongewijzigd; discover is een aanvullend pad.
- **Demo-fit**: levert de eerste trap van de beoogde UI (toon wat erin zit), op een ongezien
  dossier — de meest onderscheidende demonstratie.
- **Tijd**: clustering is O(n²) over chunks; voor honderden documenten begrensd via de bestaande
  `max_chunks_per_doc`-cap. De LLM raakt alleen de labels + per-cluster samenvatting, niet elk
  document — dus geen per-document-scorekosten zoals in `converge`.
