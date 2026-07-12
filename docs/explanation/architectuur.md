---
status: draft
last_reviewed: 2026-07-12
---

# Architectuur

Drie architectuurkeuzes dragen de hele tool: één canoniek datamodel, alle interfaces als
Protocols, en profielen als een opgeloste set drivers. Samen maken ze `cloud` ↔ `sovereign` een
**vlag, geen codewijziging**.

## Het canonieke Document-model

Elk invoerbestand wordt — ongeacht het formaat — genormaliseerd naar één pydantic-v2-model. Alle
downstream-stages zijn daardoor formaat-agnostisch: ze lezen en schrijven hetzelfde object, en
scores en beslissingen accumuleren erop.

```python
class Chunk(BaseModel):
    id: str                       # f"{document_id}:{ordinal}"
    ordinal: int
    text: str
    embedding: list[float] | None = None

class Relation(BaseModel):
    kind: Literal["thread-parent", "attachment-of", "duplicate-of", "overlaps-with"]
    target_id: str                # id van het gerelateerde Document
    evidence: str                 # waarom deze relatie is gelegd (headerwaarde, hash, cosine)

class Document(BaseModel):
    id: str                       # stabiele content+origin-hash (zie hieronder)
    source_path: str
    doc_type: Literal["email", "pdf_digital", "pdf_scanned", "office", "other"]
    metadata: dict[str, Any]      # datum, afzender, onderwerp, bronsysteem, message-id, ...
    text: str                     # genormaliseerde tekst (na OCR waar van toepassing)
    chunks: list[Chunk] = []      # alleen voor embedding/rerank van lange documenten
    relations: list[Relation] = []
    scores: dict[str, float] = {} # per stage: embed_sim, rerank, llm_relevance, final, ...
    decision: Literal["selected", "out_of_scope", "undecided"] = "undecided"
    decision_reason: str = ""     # leesbare verantwoording (cutoff-rekensom)
    rationale: str = ""           # per-document relevantie-motivatie (LLM), los van decision_reason
```

Daarnaast legt een `Criteria`-model (een lijst `Criterion{label, description}` plus de zoekvraag
en de bron — `llm` of `fallback`) de gearticuleerde relevantiedefinitie van een run vast.

### Stabiele, content-geadresseerde id

```text
id = sha256(genormaliseerde_tekst + source_path).hexdigest()[:N]
```

Deterministisch, dus een herhaalde run levert dezelfde ids op (reproduceerbaarheid), en exacte
duplicaten komen vanzelf naar boven. Het origin-pad wordt meegenomen zodat twee écht verschillende
bestanden met identieke tekst toch onderscheidbaar blijven — het `duplicate-of`-relatie-pad
behandelt "zelfde inhoud, ander pad" expliciet in plaats van ids stilletjes samen te vouwen.

## Protocols & drivers

Alle interfaces staan in `protocols.py`; concrete drivers leven apart en worden door het profiel
geselecteerd, nooit rechtstreeks geïmporteerd door een stage.

```python
class LLMProvider(Protocol):
    def complete(self, prompt: str, *, system: str | None = ...) -> str: ...
class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
class RerankerProvider(Protocol):
    def rerank(self, query: str, docs: list[str]) -> list[float]: ...   # score per doc
class Loader(Protocol):
    def can_load(self, path: Path) -> bool: ...
    def load(self, path: Path) -> list[Document]: ...  # lijst: een .eml levert body + bijlagen
```

> **Info:** drivers als `drivers/ollama.py`, `drivers/claude.py` en `drivers/eml_loader.py` worden
> via het profiel ingespoten. De pijplijn-stages weten niet welk profiel actief is — dát maakt het
> wisselen een vlag.

## Profielen

Een `Profile` (pydantic settings) mapt `--profile` naar een concrete
`(LLMProvider, EmbeddingProvider, RerankerProvider)`-triple.

- **sovereign** — volledig lokaal en air-gapped: Qwen3 via Ollama/vLLM, lokale embeddings + reranker. Default-deny egress — geen netwerkcall verlaat de machine.
- **cloud** — topkwaliteit: Claude API + hosted embeddings/rerank. Vereist egress; alleen waar de omgeving dat toestaat.
- **`--no-llm`** — wisselt LLMProvider voor een NullLLM die opwerpt bij gebruik. Criteria valt terug op de ruwe zoekvraag, scope-filter wordt regels-only en de LLM-scoring slaat over (final = rerank) — volledig deterministisch.

Geheimen (cloud-API-keys) komen uit env / SOPS+age, **nooit** uit code of configbestanden.

## Waar de LLM zit (en waar niet)

Eén regel bepaalt het: een LLM komt er alleen aan te pas bij **een oordeel onder taalkundige
ambiguïteit zónder mechanische grondwaarheid, én waar een motivatie de verdedigbaarheid
verhoogt**. Dat levert precies drie LLM-paden op, elk met de exacte prompt in de
[audit-trail](../reference/audit-trail.md):

- **Criteria-articulatie (begin)** — de zoekvraag → een expliciete, benoemde set relevantiecriteria. De geschreven definitie die een beoordelaar kan lezen en betwisten; geëxporteerd als `criteria.json`.
- **Scope-randgevallen** — alleen documenten die geen enkele deterministische regel beslist; recall-georiënteerd — UITSLUITEN alleen bij zekerheid, twijfel BEHOUDEN.
- **Relevantiescoring (eind)** — de top-K reranked kandidaten gescoord tegen de criteria: een graduele relevantiescore die de top-X drijft, mét een motivatie per document.

Alles met een mechanische grondwaarheid — threads (headers), duplicaten (hash/cosine),
regel-uitsluiting, chunking, vector-/lexicale retrieval, de cutoff-rekensom — blijft
deterministisch. De deterministische rerank fungeert als goedkope voor-trim die begrenst hoeveel
documenten de (duurdere) LLM-scoring bereiken; `--score-top-k` regelt die grens en het aantal
gescoord-versus-gedemoveerd wordt gelogd.

## Ontwerprestricties

- **Bestanden ≤ 200 regels** — drijft de opsplitsing: één bestand per loader, per driver, per
  stage. `protocols.py` bevat alleen interfaces; `models.py` alleen het datamodel.
- **Gestructureerd loggen, geen ad-hoc prints** — zie [Audit-trail](../reference/audit-trail.md).
- **Single-machine batch** — geen distributed/streaming; één map met ~1.000 documenten volstaat.
