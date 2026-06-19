"""Cloud-drivers: Claude API (LLM) + Voyage (embedding/rerank). Key-gated, niet live getest.

Deze drivers implementeren dezelfde interfaces als de soevereine varianten, maar praten met
een externe API en vereisen dus egress. Constructie is altijd toegestaan (zodat profiel-
resolutie werkt zonder keys); een echte call faalt met een duidelijke melding zodra de
benodigde sleutel ontbreekt. Sleutels komen uitsluitend uit de omgeving, nooit uit code of
een gecommit configbestand (design.md D4, provider-profiles spec).

In deze change worden de cloud-drivers niet live getest: er zijn geen sleutels en de egress
in de doelomgeving is nog onbevestigd (open vraag Q3, 26 juni).
"""

from __future__ import annotations

import json
import os
import urllib.request

CLAUDE_MODEL = "claude-opus-4-8"
VOYAGE_EMBED_MODEL = "voyage-3"
VOYAGE_RERANK_MODEL = "rerank-2"


def _require(value: str | None, env_name: str) -> str:
    if not value:
        raise RuntimeError(
            f"cloud-driver vereist {env_name} in de omgeving; geen sleutel gevonden. "
            "Sleutels horen via env/SOPS te komen, niet uit code of config."
        )
    return value


class ClaudeLLM:
    """Generatieve stap via de Claude API. Sleutel uit `ANTHROPIC_API_KEY`."""

    location = "cloud"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = CLAUDE_MODEL,
        *,
        usage_log: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.name = model
        self._usage_log = usage_log

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        key = _require(self._api_key, "ANTHROPIC_API_KEY")
        from anthropic import Anthropic  # lazy: cloud-extra hoeft niet in sovereign-runs

        client = Anthropic(api_key=key)
        kwargs: dict = {"model": self.model, "max_tokens": 1024, "temperature": 0,
                        "messages": [{"role": "user", "content": prompt}]}
        if system is not None:
            kwargs["system"] = system
        resp = client.messages.create(**kwargs)
        self._log_usage(resp)
        return "".join(block.text for block in resp.content if block.type == "text")

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


class _VoyageClient:
    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key or os.environ.get("VOYAGE_API_KEY")

    def _post(self, path: str, payload: dict) -> dict:
        key = _require(self._api_key, "VOYAGE_API_KEY")
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.voyageai.com/v1{path}",
            data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req) as resp:  # noqa: S310 — vaste, getrouste host
            return json.loads(resp.read().decode("utf-8"))


class VoyageEmbed:
    """Hosted embeddings via Voyage AI. Sleutel uit `VOYAGE_API_KEY`."""

    location = "cloud"

    def __init__(self, api_key: str | None = None, model: str = VOYAGE_EMBED_MODEL) -> None:
        self._client = _VoyageClient(api_key)
        self.model = model
        self.name = f"voyage:{model}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        res = self._client._post("/embeddings", {"model": self.model, "input": texts})
        return [[float(x) for x in row["embedding"]] for row in res["data"]]


class VoyageReranker:
    """Hosted cross-encoder rerank via Voyage AI. Sleutel uit `VOYAGE_API_KEY`."""

    location = "cloud"

    def __init__(self, api_key: str | None = None, model: str = VOYAGE_RERANK_MODEL) -> None:
        self._client = _VoyageClient(api_key)
        self.model = model
        self.name = f"voyage:{model}"

    def rerank(self, query: str, docs: list[str]) -> list[float]:
        res = self._client._post(
            "/rerank", {"model": self.model, "query": query, "documents": docs}
        )
        ordered = sorted(res["data"], key=lambda r: r["index"])
        return [float(r["relevance_score"]) for r in ordered]
