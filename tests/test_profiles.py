"""Profiel-resolutie: één vlag wisselt de drivers, geen pijplijn-code verandert (spec 3.5)."""

from zeef.config import NullLLM, ProfileName, Settings
from zeef.drivers.cloud import ClaudeLLM, VoyageEmbed, VoyageReranker
from zeef.drivers.local import HashingEmbed, LexicalReranker
from zeef.drivers.ollama import OllamaLLM
from zeef.profiles import resolve_providers


def _settings() -> Settings:
    return Settings(_env_file=None)


def test_sovereign_resolves_deterministic_local_drivers():
    bundle = resolve_providers(ProfileName.sovereign, no_llm=True, settings=_settings())
    assert isinstance(bundle.embed, HashingEmbed)
    assert isinstance(bundle.reranker, LexicalReranker)
    assert isinstance(bundle.llm, NullLLM)
    assert bundle.no_llm is True


def test_sovereign_with_llm_resolves_ollama():
    bundle = resolve_providers(ProfileName.sovereign, no_llm=False, settings=_settings())
    assert isinstance(bundle.llm, OllamaLLM)
    assert bundle.llm.location == "local"


def test_cloud_resolves_cloud_drivers_without_keys():
    # Constructie mag zonder sleutels; pas een echte call faalt zonder sleutel.
    bundle = resolve_providers(ProfileName.cloud, no_llm=False, settings=_settings())
    assert isinstance(bundle.embed, VoyageEmbed)
    assert isinstance(bundle.reranker, VoyageReranker)
    assert isinstance(bundle.llm, ClaudeLLM)
    assert bundle.embed.location == "cloud"


def test_profiles_resolve_distinct_provider_sets():
    sov = resolve_providers(ProfileName.sovereign, no_llm=False, settings=_settings())
    cloud = resolve_providers(ProfileName.cloud, no_llm=False, settings=_settings())
    assert type(sov.embed) is not type(cloud.embed)
    assert type(sov.reranker) is not type(cloud.reranker)
    assert type(sov.llm) is not type(cloud.llm)


def test_local_providers_satisfy_runtime_protocols():
    from zeef.protocols import EmbeddingProvider, RerankerProvider

    assert isinstance(HashingEmbed(), EmbeddingProvider)
    assert isinstance(LexicalReranker(), RerankerProvider)
