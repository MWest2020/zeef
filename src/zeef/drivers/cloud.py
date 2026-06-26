"""Cloud-LLM-driver: Claude API. Key-gated; sleutel uitsluitend uit de omgeving.

Implementeert dezelfde `LLMProvider`-interface als de soevereine varianten, maar praat met een
externe API en vereist dus egress. Constructie is altijd toegestaan (zodat profiel-resolutie
werkt zonder keys); een echte call faalt met een duidelijke melding zodra de benodigde sleutel
ontbreekt. Sleutels komen uitsluitend uit de omgeving, nooit uit code of een gecommit
configbestand (design.md D4, provider-profiles spec).

De Voyage-embedding/rerank-drivers staan in `drivers/voyage.py` (request-grens-bewust); `_require`
hieronder wordt door beide hergebruikt.
"""

from __future__ import annotations

import json
import os
import sys

CLAUDE_MODEL = "claude-opus-4-8"
# Beta-header die OAuth (abonnement) op /v1/messages vereist.
_OAUTH_BETA = "oauth-2025-04-20"


def _require(value: str | None, env_name: str) -> str:
    if not value:
        raise RuntimeError(
            f"cloud-driver vereist {env_name} in de omgeving; geen sleutel gevonden. "
            "Sleutels horen via env/SOPS te komen, niet uit code of config."
        )
    return value


class ClaudeLLM:
    """Generatieve stap via de Claude API.

    Twee authenticatie-modi (`auth_mode`): `api_key` (default) gebruikt een betaalde sleutel uit
    `ANTHROPIC_API_KEY`; `subscription` gebruikt een Claude-abonnement via een OAuth-credential
    (bv. `ant auth login`), dat de SDK zelf resolvet uit `ANTHROPIC_AUTH_TOKEN`. In abonnement-modus
    wordt een eventuele `ANTHROPIC_API_KEY` uit de omgeving verwijderd, zodat een achtergebleven
    betaalde sleutel nooit stilletjes credits verbruikt (de SDK kiest die anders vóór het OAuth-pad).
    """

    location = "cloud"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = CLAUDE_MODEL,
        *,
        usage_log: str | None = None,
        auth_mode: str = "api_key",
    ) -> None:
        self._auth_mode = auth_mode
        self.model = model
        self.name = model
        self._usage_log = usage_log
        if auth_mode == "subscription":
            leaked = os.environ.pop("ANTHROPIC_API_KEY", None)
            if leaked:
                sys.stderr.write(
                    "zeef: abonnement-modus actief; ANTHROPIC_API_KEY uit de omgeving genegeerd "
                    "zodat die niet wordt belast — de OAuth-abonnementscredential wordt gebruikt.\n"
                )
            self._api_key = None
        else:
            self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    def _client(self):
        from anthropic import Anthropic  # lazy: cloud-extra hoeft niet in sovereign-runs

        if self._auth_mode == "subscription":
            return Anthropic(default_headers={"anthropic-beta": _OAUTH_BETA})
        key = _require(self._api_key, "ANTHROPIC_API_KEY")
        return Anthropic(api_key=key)

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        client = self._client()
        kwargs: dict = {"model": self.model, "max_tokens": 1024, "temperature": 0,
                        "messages": [{"role": "user", "content": prompt}]}
        if system is not None:
            kwargs["system"] = system
        resp = client.messages.create(**kwargs)
        self._log_usage(resp)
        return "".join(block.text for block in resp.content if block.type == "text")

    def complete_json(
        self, prompt: str, schema: dict, *, system: str | None = None
    ) -> dict | None:
        """Structured output via geforceerde tool-use: het schema gaat als `input_schema` mee en het
        model móet de tool aanroepen (temperatuur 0). Geeft de tool-input (een dict) terug, of `None`
        als er geen tool_use-block in het antwoord zit (→ regex-fallback in score.py). Niet live
        getest (geen keys); structureel bedraad (structured-llm-score D-SCHEMA, open vraag Q3)."""
        client = self._client()
        tool = {"name": "relevantie", "description": "Geef de relevantiescore en motivatie.",
                "input_schema": schema}
        kwargs: dict = {"model": self.model, "max_tokens": 1024, "temperature": 0,
                        "messages": [{"role": "user", "content": prompt}],
                        "tools": [tool], "tool_choice": {"type": "tool", "name": "relevantie"}}
        if system is not None:
            kwargs["system"] = system
        resp = client.messages.create(**kwargs)
        self._log_usage(resp)
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use":
                inp = block.input
                return inp if isinstance(inp, dict) else None
        return None

    def _log_usage(self, resp: object) -> None:
        """Append-only tokengebruik per call (voor kostenraming). Nooit de sleutel loggen."""
        if not self._usage_log:
            return
        usage = getattr(resp, "usage", None)
        if usage is None:
            return
        import datetime

        record = {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "model": self.model,
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
        }
        with open(self._usage_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

