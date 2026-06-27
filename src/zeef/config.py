"""Profiel- en run-configuratie (design.md D4).

Een `Profile` mapt `--profile {cloud,sovereign}` naar een concrete provider-triple. De
pijplijn krijgt die providers geïnjecteerd en weet niet welk profiel actief is. `--no-llm`
vervangt de LLM door een `NullLLM`. Secrets (cloud API-keys) komen uit env/SOPS, nooit uit
config-bestanden of code.
"""

from __future__ import annotations

from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class ProfileName(str, Enum):
    cloud = "cloud"
    sovereign = "sovereign"


class CutoffMode(str, Enum):
    top_n = "top-n"
    threshold = "threshold"
    target = "target"


class Settings(BaseSettings):
    """Run-instellingen; secrets uitsluitend via env (prefix ZEEF_)."""

    model_config = SettingsConfigDict(env_prefix="ZEEF_", env_file=None, extra="ignore")

    anthropic_api_key: str | None = None
    # Authenticatie tegen de Claude-API: "api_key" = betaalde pay-per-token-sleutel uit de
    # omgeving; "subscription" = een Claude-abonnement via een OAuth-credential (bv. `ant auth
    # login`), dat tegen het plan telt i.p.v. per token. In abonnement-modus wordt een eventuele
    # ANTHROPIC_API_KEY uit de omgeving verwijderd zodat die nooit stilletjes credits verbruikt.
    auth_mode: str = "api_key"
    ollama_host: str = "http://localhost:11434"
    ollama_llm_model: str = "qwen3"
    ollama_embed_model: str = "qwen3-embedding"
    # Max. tekens die we vóór het embedden afkappen (Ollama-embeds schalen ~lineair met lengte;
    # op CPU kost een 8000-char-embed ~8 s, een 2000-char-embed ~2 s). De near-dup-embed van de
    # volledige tekst is de duurste call op een groot corpus; het dedup-/relevantiesignaal zit in de
    # leidende inhoud. Default 8000 (gedrag onveranderd); verlaag voor doorvoer op echte Woo-PDF's.
    ollama_embed_chars: int = 8000
    # Welke embedding het sovereign-profiel gebruikt: "local" (deterministisch, air-gapped
    # default) of "ollama" (modelgebaseerd via een lokale server). Reranker blijft lokaal:
    # Ollama heeft geen rerank-endpoint.
    sovereign_embed: str = "local"
    recall_bias: float = 0.0  # >0 verschuift twijfelgevallen richting insluiten
    # Cosinus-drempel waarboven een MinHash-kandidaatpaar als near-duplicate geldt (relate-stage).
    # Lager = agressiever samenvouwen (recall-risico op thematisch-verwante docs); hoger = alleen
    # vrijwel-identieke stukken vouwen. Default 0.9; stem af op de echte dataset.
    near_dup_threshold: float = 0.9
    # Cosinus-ondergrens (< near_dup_threshold) waarboven een bevestigd kandidaatpaar als
    # `overlaps-with` (partiële overlap) geldt i.p.v. duplicaat. De band [overlap_threshold,
    # near_dup_threshold) wordt zo zichtbaar; gelogd in het manifest. Conservatief.
    overlap_threshold: float = 0.7
    # Max. woorden in de per-document inhoudssamenvatting (summarise-stage, LLM). Gelogd in het manifest.
    summary_max_words: int = 100
    # Scope-filter-poort losgekoppeld van de scoring: "off" laat het scope-filter rules-only draaien
    # (LLM-randgeval overgeslagen) terwijl de relevantiescoring-LLM gewoon aan blijft. Nodig om de
    # gate-stand gelijk te houden aan een vergelijkingsrun zonder die poort. Pydantic parset
    # ZEEF_SCOPE_FILTER_LLM=off → False. Default True (gedrag onveranderd).
    scope_filter_llm: bool = True
    # Observability: print per stap een leesbaar panel (in/uit/keuze/herkomst) tijdens een run.
    # Default uit, zodat normale runs ongewijzigd blijven. CLI `--observe` of ZEEF_OBSERVE=1.
    observe: bool = False
    # LLM-backend losgekoppeld van het profiel, zodat het scope-filter-LLM onafhankelijk te
    # kiezen is (model-vergelijking): None volgt het profiel ("ollama" bij sovereign, "cloud"
    # bij cloud); expliciet "ollama" of "cloud" overschrijft dat — embeddings/rerank blijven
    # van het gekozen profiel. Zo vergelijk je modellen met alle overige variabelen constant.
    llm_backend: str | None = None
    # Het Claude-model voor de cloud-LLM (None = driver-default). Bv. een Haiku-model-id.
    cloud_llm_model: str | None = None
    # --- cloud transport-grenzen (Voyage) -------------------------------------------------
    # Voyage bound elke request (max 1.000 inputs; per-request tokenbudget). De drivers trunceren
    # per input en batchen embeddings; rerank wordt NIET gesplitst (score-onafhankelijkheid
    # onbevestigd, design D-RERANK-SPLIT) maar getrunceerd zodat de set in één call past, en faalt
    # hard als dat niet lukt. Defaults conservatief tegen de geverifieerde limieten (embeddings
    # 320K/120K-tier; rerank-2 600K totaal, query+doc ≤ 16K tok). Gelogd in het manifest.
    voyage_embed_chars: int = 16000          # per-input truncatie (~5K tok); ruim onder context
    voyage_embed_batch_size: int = 64        # < 1.000-input-limiet
    voyage_embed_batch_chars: int = 300000   # ~100K tok/req < 120K conservatieve tier
    voyage_rerank_chars: int = 4000          # per-doc truncatie; query+doc ≪ 16K-tok cap
    voyage_rerank_max_total_tokens: int = 550000  # < rerank-2 600K; harde gate (geen split)
    # Optioneel pad: append-only JSONL met tokengebruik per cloud-LLM-call (voor kosten).
    llm_usage_log: str | None = None
    # Hoeveel reranked kandidaten de LLM-relevantiescoring beoordeelt (0 = alle). Bovengrens op
    # de LLM-kosten; ruim boven het ~100-target zodat de recall-trechter niet knelt.
    llm_score_top_k: int = 250
    # --- validity-gate (deterministische pre-flight; geen LLM) ---
    # Minimaal aantal leesbare tekens; daaronder geldt een document als leeg-na-OCR en wordt het
    # uitgesloten — tenzij er laksignaal is (zie hieronder). Bewust conservatief (laag): liever
    # behouden dan een dun-maar-valide document vals uitsluiten. Afstembaar op de echte dataset.
    validity_min_chars: int = 50
    # Aandeel redactiesignaal (zwartlak/lakmarkeringen/Woo-annotaties) waarboven een document
    # ónder de tekstdrempel toch behouden blijft als 'vermoedelijk gelakt' i.p.v. leeg. Lager =
    # behoud meer (recall-veiliger). Default conservatief richting behouden.
    redaction_ratio_threshold: float = 0.10

    # --- topic-clustering (deelonderwerp-menu) ---------------------------------------------
    # Cosinus-afstandsdrempels waarop het dendrogram wordt geknipt (criterion="distance"):
    # grof = onderwerp, fijn = deelonderwerp (genest, want fijner = kleinere drempel). Hoger =
    # grovere, minder clusters. Conservatieve gokken tot de echte set bekend is; gelogd in het
    # manifest, afstembaar. Clusters kleiner dan `min_cluster_size` vallen in één "Overig".
    onderwerp_distance: float = 0.8
    deelonderwerp_distance: float = 0.5
    min_cluster_size: int = 3
    # Max. chunks per document dat de clustering in gaat (gelijkmatig bemonsterd, design T8). Begrenst
    # de O(n²)-afstandsmatrix op grote dossiers (457 p. → ~1.000+ chunks); 0 = geen cap. Gelogd in
    # het manifest. Bemonstering behoudt de topic-verdeling, dus de meerderheidsregel blijft geldig.
    max_chunks_per_doc: int = 40


class NullLLM:
    """LLM-vervanger voor `--no-llm`: weigert elke generatieve call expliciet.

    Implementeert het `LLMProvider`-protocol qua attributen, maar `complete` faalt hard —
    de aanroepende stage hoort in `--no-llm` géén LLM-pad te nemen.
    """

    name = "null-llm"
    location = "local"

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        raise RuntimeError("LLM-aanroep in --no-llm modus is niet toegestaan")
