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
    ollama_host: str = "http://localhost:11434"
    ollama_llm_model: str = "qwen3"
    ollama_embed_model: str = "qwen3-embedding"
    # Welke embedding het sovereign-profiel gebruikt: "local" (deterministisch, air-gapped
    # default) of "ollama" (modelgebaseerd via een lokale server). Reranker blijft lokaal:
    # Ollama heeft geen rerank-endpoint.
    sovereign_embed: str = "local"
    recall_bias: float = 0.0  # >0 verschuift twijfelgevallen richting insluiten
    # Cosinus-drempel waarboven een MinHash-kandidaatpaar als near-duplicate geldt (relate-stage).
    # Lager = agressiever samenvouwen (recall-risico op thematisch-verwante docs); hoger = alleen
    # vrijwel-identieke stukken vouwen. Default 0.9; stem af op de echte dataset.
    near_dup_threshold: float = 0.9
    # LLM-backend losgekoppeld van het profiel, zodat het scope-filter-LLM onafhankelijk te
    # kiezen is (model-vergelijking): None volgt het profiel ("ollama" bij sovereign, "cloud"
    # bij cloud); expliciet "ollama" of "cloud" overschrijft dat — embeddings/rerank blijven
    # van het gekozen profiel. Zo vergelijk je modellen met alle overige variabelen constant.
    llm_backend: str | None = None
    # Het Claude-model voor de cloud-LLM (None = driver-default). Bv. een Haiku-model-id.
    cloud_llm_model: str | None = None
    # Optioneel pad: append-only JSONL met tokengebruik per cloud-LLM-call (voor kosten).
    llm_usage_log: str | None = None
    # Hoeveel reranked kandidaten de LLM-relevantiescoring beoordeelt (0 = alle). Bovengrens op
    # de LLM-kosten; ruim boven het ~100-target zodat de recall-trechter niet knelt.
    llm_score_top_k: int = 250


class NullLLM:
    """LLM-vervanger voor `--no-llm`: weigert elke generatieve call expliciet.

    Implementeert het `LLMProvider`-protocol qua attributen, maar `complete` faalt hard —
    de aanroepende stage hoort in `--no-llm` géén LLM-pad te nemen.
    """

    name = "null-llm"
    location = "local"

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        raise RuntimeError("LLM-aanroep in --no-llm modus is niet toegestaan")
