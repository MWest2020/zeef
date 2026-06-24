## ADDED Requirements

### Requirement: discover-commando
Het systeem SHALL een `zeef discover <docs>`-commando bieden dat de discover-capability draait: het
volledige corpus inlezen en de onderwerp-landkaart opleveren zónder query. Het SHALL de uitvoer naar
een runmap schrijven met dezelfde structuur als `converge` (JSON-resultaat, `audit.jsonl`, en een
`report/`-viewer). Het SHALL het profiel en de embedding-bron respecteren (sovereign/cloud,
lokaal/Ollama-embeddings), en `--no-llm` ondersteunen (TF-IDF-labels, geen samenvattingen). Het
SHALL de clustering-parameters (`min_cluster_size`, knip-afstanden, `max_chunks_per_doc`) als
opties aanbieden met discover-passende defaults.

#### Scenario: Discover draaien en landkaart opleveren
- **WHEN** `zeef discover ./docs --out ./run` draait
- **THEN** wordt het corpus geïngest, gededupliceerd, geëmbed en geclusterd zonder query
- **AND** de runmap bevat de onderwerp-landkaart (JSON), `audit.jsonl` en een `report/`-viewer
- **AND** er verschijnt een beknopte samenvatting (aantal onderwerpen, deelonderwerpen, documenten) in de terminal

#### Scenario: Discover zonder LLM
- **WHEN** `zeef discover ./docs --no-llm` draait
- **THEN** worden de clusters met TF-IDF-labels benoemd zonder model-call
- **AND** er worden geen per-cluster samenvattingen geproduceerd
