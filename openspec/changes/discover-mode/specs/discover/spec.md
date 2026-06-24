## ADDED Requirements

### Requirement: Onderwerp-landkaart zonder query
Het systeem SHALL over het volledige corpus, zónder dat een query wordt meegegeven, een genestte
onderwerp/deelonderwerp-landkaart opleveren. Het SHALL daartoe `ingest`, de validity-gate en de
dedup/relate-stap draaien, de chunks embedden, en vervolgens de bestaande tweelaags-clustering
(`cluster_topics`) over het volledige valide, gededupliceerde corpus toepassen — níét over een
query-gedreven selectie. De query-gedreven stages (criteria, retrieve, rerank, score, select)
SHALL in deze modus worden overgeslagen.

#### Scenario: Ontdekken op een ongezien corpus
- **WHEN** `discover` over een map met documenten draait, zonder query
- **THEN** wordt het corpus geïngest, op validiteit gefilterd en gededupliceerd
- **AND** de chunks worden geëmbed en tweelaags geclusterd tot onderwerpen en geneste deelonderwerpen
- **AND** er wordt geen query-gedreven selectie uitgevoerd

#### Scenario: Hergebruik van de bestaande clustering
- **WHEN** de clustering draait
- **THEN** wordt `cluster_topics` (dezelfde stage als in `converge`) gebruikt, gevoed met het
  volledige valide corpus in plaats van `selected`
- **AND** het resultaat is deterministisch en genest (elk document precies één onderwerp + één deelonderwerp)

### Requirement: Per-cluster label en samenvatting
Het systeem SHALL per ontdekt cluster een kort label leveren (via de bestaande `label_cluster`:
LLM, of TF-IDF onder `--no-llm`) en een korte samenvatting van de kern van dat cluster, gebaseerd
op de representatieve leden (medoid-eerst). De LLM SHALL alleen de labels en de per-cluster
samenvatting raken — níét elk document afzonderlijk — zodat de kosten begrensd blijven. Onder
`--no-llm` SHALL de samenvatting vervallen en blijven de TF-IDF-labels over.

#### Scenario: Cluster-samenvatting in plaats van per-document
- **WHEN** de landkaart wordt opgebouwd met een LLM-profiel
- **THEN** krijgt elk cluster een label en een samenvatting op basis van zijn representatieve leden
- **AND** er wordt niet per document een aparte samenvatting-call gedaan

#### Scenario: Deterministisch zonder LLM
- **WHEN** `discover --no-llm` draait
- **THEN** worden labels uit distinctieve termen (TF-IDF) gebouwd, zonder enige model-call
- **AND** er worden geen per-cluster samenvattingen geproduceerd

### Requirement: Navolgbare discover-uitvoer
Het systeem SHALL de ontdekte landkaart naar een runmap schrijven: de genestte structuur
(onderwerpen → deelonderwerpen → `doc_id`'s, met labels en samenvattingen) als JSON, samen met de
append-only `audit.jsonl` en een `report/`-viewer. De gebruikte parameters (clustering-afstanden,
`min_cluster_size`, embedding-bron) SHALL in het run-manifest worden vastgelegd.

#### Scenario: Runmap met landkaart en audit
- **WHEN** `discover` klaar is
- **THEN** bevat de runmap de onderwerp-landkaart als JSON, `audit.jsonl`, en een `report/`-viewer
- **AND** de clustering-parameters en de embedding-bron staan in het manifest
