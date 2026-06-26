"""LLM-scoring (converge-ranking D14/D22): `llm_relevance` + motivatie als side-score.

`final` blijft de passage-cosine (gezet in retrieve); score raakt 'm niet aan en demoveert niemand
(geen recall-gate). De top-K op `final` krijgt een LLM-toelichting; de rest blijft onaangeroerd.
"""

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
    out = []
    for i in range(n):
        d = Document(id=f"d{i:02d}", source_path=f"/d{i}", doc_type="email", text=f"tekst {i}")
        # `final` is hier de (reeds in retrieve gezette) cosine; aflopend zodat de top-K-keuze
        # op `final` dezelfde volgorde geeft als de invoer.
        d.scores["rerank"] = d.scores["final"] = 1.0 - i * 0.01
        out.append(d)
    return out


def _criteria():
    return Criteria(query="q", items=[Criterion(label="publicatieclausule", description="x")], source="llm")


def _bundle(llm, no_llm):
    return ProviderBundle(llm=llm, embed=HashingEmbed(), reranker=LexicalReranker(), no_llm=no_llm)


def _events(audit):
    return [json.loads(line) for line in audit.path.read_text(encoding="utf-8").splitlines()]


def test_scoring_sets_relevance_and_rationale_not_final(audit):
    docs = _docs(3)
    fake = FakeLLM()
    score(docs, _criteria(), _bundle(fake, no_llm=False), audit, "q", top_k=0)
    assert docs[0].scores["llm_relevance"] == 0.9
    assert docs[0].scores["final"] == 1.0  # cosine onaangeroerd door score
    assert docs[0].rationale == "raakt criterium publicatieclausule"
    assert len(fake.calls) == 3  # top_k=0 → alle gescoord
    evts = [e for e in _events(audit) if e["action"] == "llm-score"]
    assert len(evts) == 3 and all(e["prompt"] and e["model"] == "fake-llm" for e in evts)


def test_top_k_scores_subset_without_demotion(audit):
    docs = _docs(5)
    fake = FakeLLM()
    score(docs, _criteria(), _bundle(fake, no_llm=False), audit, "q", top_k=2)
    assert len(fake.calls) == 2
    # top-K krijgt een LLM-toelichting; `final` blijft de cosine.
    assert docs[0].scores["llm_relevance"] == 0.9 and docs[1].scores["llm_relevance"] == 0.8
    assert docs[0].scores["final"] == 1.0 and docs[1].scores["final"] == 1.0 - 0.01
    # de rest: GEEN demotion, GEEN llm_relevance, GEEN rationale — `final` onaangeroerd.
    for i in range(2, 5):
        assert "llm_relevance" not in docs[i].scores
        assert docs[i].scores["final"] == 1.0 - i * 0.01
        assert docs[i].rationale == ""
    done = [e for e in _events(audit) if e["action"] == "score-complete"][0]
    assert done["inputs"] == {"query": "q", "top_k": 2, "scored": 2, "candidates": 5}


def test_no_llm_skips_and_keeps_cosine_final(audit):
    docs = _docs(3)
    fake = FakeLLM()
    score(docs, _criteria(), _bundle(fake, no_llm=True), audit, "q", top_k=0)
    assert fake.calls == []
    assert docs[0].scores["final"] == 1.0  # cosine onaangeroerd
    assert "llm_relevance" not in docs[0].scores
    assert [e for e in _events(audit) if e["action"] == "skipped"]


def test_unparseable_answer_scores_zero_relevance_without_crash(audit):
    class Garbage:
        name = "fake-llm"
        location = "local"

        def complete(self, prompt, *, system=None):
            return "ik weet het niet"

    docs = _docs(1)
    score(docs, _criteria(), _bundle(Garbage(), no_llm=False), audit, "q", top_k=0)
    assert docs[0].scores["llm_relevance"] == 0.0
    assert docs[0].rationale == "ik weet het niet"
    assert docs[0].scores["final"] == 1.0  # geen demotion: cosine onaangeroerd
