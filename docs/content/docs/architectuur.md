---
title: Architectuur
weight: 3
---

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
    scores: dict[str, float] = {} # per stage: embed_sim, rerank, final, ...
    decision: Literal["selected", "out_of_scope", "undecided"] = "undecided"
    decision_reason: str = ""     # leesbare verantwoording
```

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

{{< callout type="info" >}}
  Drivers als `drivers/ollama.py`, `drivers/claude.py` en `drivers/eml_loader.py` worden via het
  profiel ingespoten. De pijplijn-stages weten niet welk profiel actief is — dát maakt het
  wisselen een vlag.
{{< /callout >}}

## Profielen

Een `Profile` (pydantic settings) mapt `--profile` naar een concrete
`(LLMProvider, EmbeddingProvider, RerankerProvider)`-triple.

{{< cards >}}
  {{< card title="sovereign" icon="lock-closed"
        subtitle="Volledig lokaal en air-gapped: Qwen3 via Ollama/vLLM, lokale embeddings + reranker. Default-deny egress — geen netwerkcall verlaat de machine." >}}
  {{< card title="cloud" icon="cloud"
        subtitle="Topkwaliteit: Claude API + hosted embeddings/rerank. Vereist egress; alleen waar de omgeving dat toestaat." >}}
  {{< card title="--no-llm" icon="ban"
        subtitle="Wisselt LLMProvider voor een NullLLM die opwerpt bij gebruik. Scope-filter wordt regels-only, selectie embed+rerank-only — volledig deterministisch." >}}
{{< /cards >}}

Geheimen (cloud-API-keys) komen uit env / SOPS+age, **nooit** uit code of configbestanden.

## Ontwerprestricties

- **Bestanden ≤ 200 regels** — drijft de opsplitsing: één bestand per loader, per driver, per
  stage. `protocols.py` bevat alleen interfaces; `models.py` alleen het datamodel.
- **Gestructureerd loggen, geen ad-hoc prints** — zie [Audit-trail](../audit-trail).
- **Single-machine batch** — geen distributed/streaming; één map met ~1.000 documenten volstaat.
