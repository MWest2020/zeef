"""Cloud-LLM authenticatie-modi (provider-profiles spec): api-key vs abonnement (OAuth).

Borgt de billing-veiligheid: in abonnement-modus mag een achtergebleven betaalde sleutel
nooit worden gebruikt — hij wordt uit de omgeving verwijderd en de client krijgt geen
`api_key`, wél de OAuth-beta-header. In api-key-modus faalt een call hard zonder sleutel.
"""

import pytest

from zeef.drivers.cloud import ClaudeLLM


class _FakeBlock:
    type = "text"
    text = "SCORE: 42\nMOTIVATIE: test"


class _FakeMessages:
    def __init__(self, recorder):
        self._rec = recorder

    def create(self, **kwargs):
        class _Resp:
            content = [_FakeBlock()]
            usage = None
        return _Resp()


class _FakeAnthropic:
    """Legt de constructor-kwargs vast en levert een dummy messages-API."""

    last_kwargs = None

    def __init__(self, **kwargs):
        _FakeAnthropic.last_kwargs = kwargs
        self.messages = _FakeMessages(kwargs)


@pytest.fixture
def fake_sdk(monkeypatch):
    # Lazy import: de suite moet collecteren zónder de optionele `cloud`-dep; deze cloud-only
    # tests skippen netjes als `anthropic` ontbreekt (de tests die de SDK niet raken draaien wel).
    anthropic = pytest.importorskip("anthropic")
    _FakeAnthropic.last_kwargs = None
    monkeypatch.setattr(anthropic, "Anthropic", _FakeAnthropic)
    return _FakeAnthropic


def test_subscription_pops_paid_key_from_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-paid-should-be-removed")
    ClaudeLLM(auth_mode="subscription")
    import os
    assert "ANTHROPIC_API_KEY" not in os.environ


def test_subscription_client_uses_oauth_header_and_no_key(fake_sdk, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    llm = ClaudeLLM(auth_mode="subscription", model="claude-haiku-4-5-20251001")
    llm.complete("hallo", system="sys")
    kw = fake_sdk.last_kwargs
    assert "api_key" not in kw
    assert kw["default_headers"]["anthropic-beta"] == "oauth-2025-04-20"


def test_api_key_mode_requires_key(monkeypatch):
    # complete() importeert de SDK (lazy) vóór de key-check, dus deze test heeft de cloud-dep nodig.
    pytest.importorskip("anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    llm = ClaudeLLM(auth_mode="api_key")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        llm.complete("hallo")


def test_api_key_mode_passes_key_to_client(fake_sdk):
    llm = ClaudeLLM("sk-test-key", auth_mode="api_key")
    llm.complete("hallo")
    assert fake_sdk.last_kwargs["api_key"] == "sk-test-key"
    assert "default_headers" not in fake_sdk.last_kwargs
