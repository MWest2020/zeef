"""LLM-scoring (retrieve-rerank-spec): final = llm_relevance + motivatie; top-K demoveert de rest."""

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
        d.scores["rerank"] = d.scores["final"] = 1.0 - i * 0.01
        out.append(d)
    return out


def _criteria():
    return Criteria(query="q", items=[Criterion(label="publicatieclausule", description="x")], source="llm")


def _bundle(llm, no_llm):
    return ProviderBundle(llm=llm, embed=HashingEmbed(), reranker=LexicalReranker(), no_llm=no_llm)


def _events(audit):
    return [json.loads(line) for line in audit.path.read_text(encoding="utf-8").splitlines()]


def test_scoring_sets_relevance_rationale_and_final(audit):
    docs = _docs(3)
    fake = FakeLLM()
    score(docs, _criteria(), _bundle(fake, no_llm=False), audit, "q", top_k=0)
    assert docs[0].scores["llm_relevance"] == 0.9 and docs[0].scores["final"] == 0.9
    assert docs[0].rationale == "raakt criterium publicatieclausule"
    assert len(fake.calls) == 3  # top_k=0 → alle gescoord
    evts = [e for e in _events(audit) if e["action"] == "llm-score"]
    assert len(evts) == 3 and all(e["prompt"] and e["model"] == "fake-llm" for e in evts)


def test_top_k_demotes_the_rest(audit):
    docs = _docs(5)
    fake = FakeLLM()
    score(docs, _criteria(), _bundle(fake, no_llm=False), audit, "q", top_k=2)
    assert len(fake.calls) == 2
    assert docs[0].scores["final"] == 0.9 and docs[1].scores["final"] == 0.8
    for d in docs[2:]:
        assert d.scores["final"] == 0.0
        assert "buiten top-K" in d.rationale
    done = [e for e in _events(audit) if e["action"] == "score-complete"][0]
    assert done["inputs"] == {"query": "q", "top_k": 2, "scored": 2, "demoted": 3}


def test_no_llm_skips_and_keeps_rerank_final(audit):
    docs = _docs(3)
    fake = FakeLLM()
    score(docs, _criteria(), _bundle(fake, no_llm=True), audit, "q", top_k=0)
    assert fake.calls == []
    assert docs[0].scores["final"] == 1.0  # rerank-score onaangeroerd
    assert "llm_relevance" not in docs[0].scores
    assert [e for e in _events(audit) if e["action"] == "skipped"]


def test_unparseable_answer_scores_zero_without_crash(audit):
    class Garbage:
        name = "fake-llm"
        location = "local"

        def complete(self, prompt, *, system=None):
            return "ik weet het niet"

    docs = _docs(1)
    score(docs, _criteria(), _bundle(Garbage(), no_llm=False), audit, "q", top_k=0)
    assert docs[0].scores["final"] == 0.0
    assert docs[0].rationale == "ik weet het niet"
