"""Soevereine, modelgebaseerde drivers via een lokale Ollama/vLLM-server (design.md D4).

Deze drivers blijven binnen de machine (location=local) maar vereisen een draaiende lokale
server met de gewenste gewichten (bijv. Qwen3). Ze worden *niet* live getest in deze change:
de air-gapped acceptatie gebruikt de deterministische `local.py`-drivers. Hier staat de
modelgebaseerde variant achter exact dezelfde interface, te kiezen wanneer gewichten en
server vooraf zijn klaargezet.

Alleen de standaardbibliotheek (`urllib`) wordt gebruikt, zodat er geen extra afhankelijkheid
nodig is. Elke call gaat naar `http://localhost:11434` (of `ZEEF_OLLAMA_HOST`).
"""

from __future__ import annotations

import json
import urllib.request


class _OllamaClient:
    def __init__(self, host: str) -> None:
        self.host = host.rstrip("/")

    def _post(self, path: str, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}{path}", data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:  # noqa: S310 — lokale loopback, geen egress
            return json.loads(resp.read().decode("utf-8"))


# Het Ollama-embeddings-endpoint geeft HTTP 500 op zeer lange invoer (bevestigd: ~99k tekens
# faalt, ~8k werkt). Echte Woo-PDF's zijn fors, dus kappen we de tekst af op een veilige lengte
# vóór we embedden. Dat is verantwoord: een embedding representeert vooral de leidende inhoud
# (titel, partijen, onderwerp — waar het relevantiesignaal zit), en het alternatief is een crash
# op de echte dataset. De afkaplengte is instelbaar mocht een model/server meer aankunnen.
_EMBED_CHAR_BUDGET = 8000


class OllamaEmbed:
    """Embeddings via een lokaal Ollama-model (bijv. `nomic-embed-text`)."""

    location = "local"

    def __init__(
        self, host: str, model: str = "nomic-embed-text", *, char_budget: int = _EMBED_CHAR_BUDGET
    ) -> None:
        self._client = _OllamaClient(host)
        self.model = model
        self.name = f"ollama:{model}"
        self._char_budget = char_budget

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            clipped = text[: self._char_budget]
            res = self._client._post("/api/embeddings", {"model": self.model, "prompt": clipped})
            out.append([float(x) for x in res["embedding"]])
        return out


class OllamaLLM:
    """Generatieve stap via een lokaal Ollama-model (bijv. Qwen3). Temperatuur 0.

    `think=False` zet de redeneer-modus van Qwen3-achtige modellen uit: voor een korte
    in/uit-scope-classificatie is een denkspoor onnodig en op CPU onbetaalbaar traag.
    `num_predict` begrenst de uitvoer. Beide zijn driver-instellingen; de aan de stage
    doorgegeven prompt blijft ongewijzigd (de audit-log legt exact díe prompt vast).
    """

    location = "local"

    def __init__(
        self, host: str, model: str = "qwen3", *, think: bool = False, num_predict: int = 64
    ) -> None:
        self._client = _OllamaClient(host)
        self.model = model
        self.name = f"ollama:{model}"
        self.think = think
        self.num_predict = num_predict

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": self.think,
            "options": {"temperature": 0, "num_predict": self.num_predict},
        }
        if system is not None:
            payload["system"] = system
        res = self._client._post("/api/generate", payload)
        return res.get("response", "")
