"""LLM-scoring (converge-final-flow): llm_relevance + motivatie als side-score/"waarom"-gloss;
raakt `final` NIET en demoveert NIET — de selector is de cosine (`final`, gezet in retrieve)."""

import json

from zeef.drivers.local import HashingEmbed, LexicalReranker
from zeef.models import Criteria, Criterion, Document
from zeef.pipeline.score import score
from zeef.profiles import ProviderBundle


class FakeLLM:
    """Scoort op volgorde: eerste doc 90, daarna 80, 70, ... met expliciete motivatie."""

    name = "fake-llm"
    location = "local"

    def __init__(self):
        self.calls = []

    def complete(self, prompt, *, system=None):
        self.calls.append(prompt)
        n = 90 - 10 * (len(self.calls) - 1)
        return f"SCORE: {n}\nMOTIVATIE: raakt criterium publicatieclausule"


def _docs(n):
    """Simuleer de staat ná retrieve+rerank: `final` is de cosine, `rerank` de side-score."""
    out = []
    for i in range(n):
        d = Document(id=f"d{i:02d}", source_path=f"/d{i}", doc_type="email", text=f"tekst {i}")
        d.scores["rerank"] = d.scores["final"] = 1.0 - i * 0.01
        out.append(d)
    return out


def _criteria():
    return Criteria(query="q", items=[Criterion(label="publicatieclausule", description="x")], source="llm")


def _bundle(llm, no_llm):
    return ProviderBundle(llm=llm, embed=HashingEmbed(), reranker=LexicalReranker(), no_llm=no_llm)


def _events(audit):
    return [json.loads(line) for line in audit.path.read_text(encoding="utf-8").splitlines()]


def test_scoring_sets_relevance_and_rationale_but_not_final(audit):
    docs = _docs(3)
    fake = FakeLLM()
    score(docs, _criteria(), _bundle(fake, no_llm=False), audit, "q", top_k=0)
    assert docs[0].scores["llm_relevance"] == 0.9          # gloss gezet
    assert docs[0].scores["final"] == 1.0                  # cosine onaangeroerd door score
    assert docs[0].rationale == "raakt criterium publicatieclausule"
    assert len(fake.calls) == 3  # top_k=0 → alle gescoord
    evts = [e for e in _events(audit) if e["action"] == "llm-score"]
    assert len(evts) == 3 and all(e["prompt"] and e["model"] == "fake-llm" for e in evts)


def test_top_k_limits_gloss_not_selection(audit):
    docs = _docs(5)
    fake = FakeLLM()
    score(docs, _criteria(), _bundle(fake, no_llm=False), audit, "q", top_k=2)
    assert len(fake.calls) == 2
    assert docs[0].scores["llm_relevance"] == 0.9 and docs[1].scores["llm_relevance"] == 0.8
    # Niet-gescoorde docs houden hun cosine-`final` — géén demotie naar 0.0, géén "buiten top-K".
    for i, d in enumerate(docs[2:], start=2):
        assert "llm_relevance" not in d.scores
        assert d.scores["final"] == 1.0 - i * 0.01
        assert d.rationale == ""
    done = [e for e in _events(audit) if e["action"] == "score-complete"][0]
    assert done["inputs"] == {"query": "q", "top_k": 2, "scored": 2, "not_scored_keep_cosine": 3}


def test_no_llm_skips_and_keeps_cosine_final(audit):
    docs = _docs(3)
    fake = FakeLLM()
    score(docs, _criteria(), _bundle(fake, no_llm=True), audit, "q", top_k=0)
    assert fake.calls == []
    assert docs[0].scores["final"] == 1.0  # cosine onaangeroerd (geen LLM, geen rerank-overschrijving)
    assert "llm_relevance" not in docs[0].scores
    assert [e for e in _events(audit) if e["action"] == "skipped"]


def test_unparseable_answer_scores_zero_relevance_keeps_final(audit):
    class Garbage:
        name = "fake-llm"
        location = "local"

        def complete(self, prompt, *, system=None):
            return "ik weet het niet"

    docs = _docs(1)
    score(docs, _criteria(), _bundle(Garbage(), no_llm=False), audit, "q", top_k=0)
    assert docs[0].scores["llm_relevance"] == 0.0   # gloss 0, geen crash
    assert docs[0].scores["final"] == 1.0           # cosine onaangeroerd
    assert docs[0].rationale == "ik weet het niet"
