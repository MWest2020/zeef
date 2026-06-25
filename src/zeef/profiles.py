"""Profiel → concrete provider-triple (design.md D3/D4).

Eén plek die `--profile {cloud,sovereign}` en `--no-llm` vertaalt naar een
`(LLMProvider, EmbeddingProvider, RerankerProvider)`. De pijplijn-stages krijgen deze
bundel geïnjecteerd en weten niet welk profiel actief is — dát maakt het wisselen van
profiel een vlag i.p.v. een codewijziging.

`sovereign` kiest bewust de deterministische, air-gapped `local`-drivers als default, zodat
een acceptatierun zonder netwerk en zonder modelgewichten werkt. De modelgebaseerde
soevereine drivers (Ollama) en de cloud-drivers staan achter dezelfde interfaces en worden
hier geconstrueerd, maar elke echte call is gated op server-bereikbaarheid resp. een sleutel.
"""

from __future__ import annotations

from dataclasses import dataclass

from zeef.config import NullLLM, ProfileName, Settings
from zeef.protocols import EmbeddingProvider, LLMProvider, RerankerProvider


@dataclass(frozen=True)
class ProviderBundle:
    """De drie providers die een run gebruikt, plus of de LLM is uitgeschakeld."""

    llm: LLMProvider
    embed: EmbeddingProvider
    reranker: RerankerProvider
    no_llm: bool


def resolve_providers(
    profile: ProfileName, no_llm: bool, settings: Settings
) -> ProviderBundle:
    """Bouw de provider-triple voor dit profiel. Drivers worden lazy geïmporteerd."""
    embed, reranker = _resolve_embed_rerank(profile, settings)
    llm = _resolve_llm(profile, no_llm, settings)
    return ProviderBundle(llm=llm, embed=embed, reranker=reranker, no_llm=no_llm)


def _resolve_embed_rerank(
    profile: ProfileName, settings: Settings
) -> tuple[EmbeddingProvider, RerankerProvider]:
    if profile is ProfileName.sovereign:
        from zeef.drivers.local import HashingEmbed, LexicalReranker

        # Reranker blijft lokaal-deterministisch: Ollama kent geen rerank-endpoint.
        if settings.sovereign_embed == "ollama":
            from zeef.drivers.ollama import OllamaEmbed

            return OllamaEmbed(
                settings.ollama_host, settings.ollama_embed_model,
                char_budget=settings.ollama_embed_chars,
            ), LexicalReranker()
        # Air-gapped default: deterministisch, geen netwerk of gewichten nodig.
        return HashingEmbed(), LexicalReranker()
    if profile is ProfileName.cloud:
        from zeef.drivers.voyage import VoyageEmbed, VoyageReranker

        return (
            VoyageEmbed(
                embed_chars=settings.voyage_embed_chars,
                batch_size=settings.voyage_embed_batch_size,
                batch_chars=settings.voyage_embed_batch_chars,
            ),
            VoyageReranker(
                rerank_chars=settings.voyage_rerank_chars,
                max_total_tokens=settings.voyage_rerank_max_total_tokens,
            ),
        )
    raise ValueError(f"onbekend profiel: {profile!r}")


def _resolve_llm(
    profile: ProfileName, no_llm: bool, settings: Settings
) -> LLMProvider:
    if no_llm:
        return NullLLM()
    # Backend volgt het profiel tenzij expliciet overschreven (model-vergelijking).
    backend = settings.llm_backend or (
        "cloud" if profile is ProfileName.cloud else "ollama"
    )
    if backend == "ollama":
        from zeef.drivers.ollama import OllamaLLM

        return OllamaLLM(settings.ollama_host, settings.ollama_llm_model)
    if backend == "cloud":
        from zeef.drivers.cloud import ClaudeLLM

        model = settings.cloud_llm_model
        kwargs = {"model": model} if model else {}
        return ClaudeLLM(
            settings.anthropic_api_key, usage_log=settings.llm_usage_log,
            auth_mode=settings.auth_mode, **kwargs
        )
    raise ValueError(f"onbekende llm-backend: {backend!r}")
