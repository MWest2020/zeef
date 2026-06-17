"""Profiel- en run-configuratie (design.md D4).

Een `Profile` mapt `--profile {cloud,sovereign}` naar een concrete provider-triple. De
pijplijn krijgt die providers geïnjecteerd en weet niet welk profiel actief is. `--no-llm`
vervangt de LLM door een `NullLLM`. Secrets (cloud API-keys) komen uit env/SOPS, nooit uit
config-bestanden of code.
"""

from __future__ import annotations

from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict

from zeef.protocols import LLMProvider


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
    recall_bias: float = 0.0  # >0 verschuift twijfelgevallen richting insluiten


class NullLLM:
    """LLM-vervanger voor `--no-llm`: weigert elke generatieve call expliciet.

    Implementeert het `LLMProvider`-protocol qua attributen, maar `complete` faalt hard —
    de aanroepende stage hoort in `--no-llm` géén LLM-pad te nemen.
    """

    name = "null-llm"
    location = "local"

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        raise RuntimeError("LLM-aanroep in --no-llm modus is niet toegestaan")


def resolve_llm(profile: ProfileName, no_llm: bool, settings: Settings) -> LLMProvider:
    """Kies de LLM-provider op basis van profiel en --no-llm.

    Concrete drivers worden lazy geïmporteerd zodat het skelet importeerbaar blijft zonder
    de profiel-specifieke (zwaardere) dependencies.
    """
    if no_llm:
        return NullLLM()
    # Concrete drivers volgen in de implementatiefase (tasks 3.3 / 3.4).
    raise NotImplementedError(
        f"LLM-driver voor profiel '{profile.value}' nog niet geïmplementeerd "
        "(zie openspec change converge-mvp, taken 3.3/3.4)."
    )
