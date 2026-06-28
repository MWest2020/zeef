"""Deterministische, volledig lokale providers — de air-gapped MVP-default voor `sovereign`.

Deze drivers hebben *geen* netwerk en *geen* modelgewichten nodig. Ze zijn maximaal
soeverein en maximaal navolgbaar: dezelfde invoer geeft altijd dezelfde uitvoer, zodat een
`--profile sovereign --no-llm` run volledig reproduceerbaar én air-gapped is (zie design.md
D4 en de risicoparagraaf: het lokale-model-footprint hoeft de dag niet te halen).

`HashingEmbed` is een feature-hashing (bag-of-words) embedding; `LexicalReranker` een
BM25-achtige lexicale herrangschikking. De zwaardere modelgebaseerde soevereine drivers
(Ollama, cross-encoder) leven achter dezelfde interfaces in `ollama.py` en worden alleen
gekozen wanneer een server/gewichten aanwezig zijn.
"""

from __future__ import annotations

import hashlib
import math

from zeef.similarity import l2_normalize, tokenize

EMBED_DIM = 256


def _bucket(token: str, dim: int) -> int:
    """Stabiele bucket-index via sha1 (los van Python's hash-seed)."""
    h = hashlib.sha1(token.encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big") % dim


class HashingEmbed:
    """Feature-hashing embedding (term-frequency), L2-genormaliseerd. Deterministisch."""

    name = "hashing-embed-v1"
    location = "local"

    def __init__(self, dim: int = EMBED_DIM) -> None:
        self.dim = dim

    def embed(self, texts: list[str], *, progress=None) -> list[list[float]]:
        out: list[list[float]] = []
        total = len(texts)
        for i, text in enumerate(texts, start=1):
            vec = [0.0] * self.dim
            for tok in tokenize(text):
                vec[_bucket(tok, self.dim)] += 1.0
            out.append(l2_normalize(vec))
            if progress is not None:
                progress(i, total)
        return out


class LexicalReranker:
    """BM25-achtige lexicale herrangschikking — deterministisch, geen model nodig.

    Per document een relevantiescore t.o.v. de query op basis van termfrequenties en
    inverse documentfrequentie binnen de kandidatenset. Voldoende om de eerste-pass
    embedding-ordening te verfijnen zonder een cross-encoder te hoeven laden.
    """

    name = "lexical-rerank-v1"
    location = "local"

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b

    def rerank(self, query: str, docs: list[str]) -> list[float]:
        q_terms = set(tokenize(query))
        doc_tokens = [tokenize(d) for d in docs]
        n = len(docs)
        if n == 0:
            return []
        avg_len = sum(len(t) for t in doc_tokens) / n or 1.0
        # df per queryterm binnen de kandidatenset.
        df = {t: sum(1 for toks in doc_tokens if t in toks) for t in q_terms}
        scores: list[float] = []
        for toks in doc_tokens:
            length = len(toks) or 1
            score = 0.0
            for t in q_terms:
                tf = toks.count(t)
                if tf == 0:
                    continue
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                denom = tf + self.k1 * (1 - self.b + self.b * length / avg_len)
                score += idf * (tf * (self.k1 + 1)) / denom
            scores.append(score)
        return _normalize_scores(scores)


def _normalize_scores(scores: list[float]) -> list[float]:
    """Schaal naar 0..1 zodat scores tussen runs/stages vergelijkbaar blijven."""
    if not scores:
        return scores
    hi = max(scores)
    if hi <= 0.0:
        return [0.0 for _ in scores]
    return [s / hi for s in scores]
