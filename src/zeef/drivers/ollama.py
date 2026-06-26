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
import sys
import time
import urllib.error
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
        self._dim = 0  # modeldimensie, onthouden zodra één embed lukt (voor uniforme fallback)

    def embed(self, texts: list[str]) -> list[list[float]]:
        # Per tekst: clip, dan één retry op een transiënte server-fout (Ollama geeft op een groot
        # corpus soms een 500 na honderden calls). Faalt het hardnekkig, of geeft het model een lege
        # embedding (waargenomen bij lege invoer), dan vullen we een nulvector van de modeldimensie —
        # zo blijven de vectorlengtes uniform (cosine eist dat) en routeert de clustering het
        # document deterministisch naar "Overig" i.p.v. de hele run te laten crashen. De dimensie
        # wordt onthouden over calls heen (`self._dim`), zodat ook een volledig mislukte batch
        # uniforme nulvectoren geeft zolang ergens eerder één embed lukte. Pas als nog nóóit één
        # embed lukte is de dimensie onbekend en geven we een lege vector (lengte 0, óók uniform).
        raw: list[list[float] | None] = []
        for text in texts:
            clipped = text[: self._char_budget].strip()
            vec = self._embed_one(clipped) if clipped else None
            if vec:
                self._dim = len(vec)
            raw.append(vec)
        return [v if v else [0.0] * self._dim for v in raw]

    def _embed_one(self, prompt: str) -> list[float] | None:
        for attempt in (1, 2):
            try:
                res = self._client._post(
                    "/api/embeddings", {"model": self.model, "prompt": prompt}
                )
                emb = res.get("embedding") or []
                return [float(x) for x in emb] if emb else None
            except (urllib.error.HTTPError, urllib.error.URLError) as exc:
                if attempt == 1:
                    time.sleep(0.5)
                    continue
                print(f"ollama-embed: {exc} na retry — nulvector-fallback (→ Overig)",
                      file=sys.stderr)
                return None
        return None


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

    def complete_json(
        self, prompt: str, schema: dict, *, system: str | None = None
    ) -> dict | None:
        """Structured output via Ollama's `format` (JSON-schema) op `/api/generate`. Geeft het
        geparste object terug, of `None` bij ongeldige/lege JSON (→ regex-fallback in score.py).
        `num_predict` krijgt een ruimere ondergrens zodat een korte motivatie-zin niet wordt
        afgekapt midden in de JSON."""
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": self.think,
            "format": schema,
            "options": {"temperature": 0, "num_predict": max(self.num_predict, 256)},
        }
        if system is not None:
            payload["system"] = system
        res = self._client._post("/api/generate", payload)
        try:
            obj = json.loads(res.get("response", ""))
        except (json.JSONDecodeError, TypeError):
            return None
        return obj if isinstance(obj, dict) else None
