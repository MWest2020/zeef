"""Structured LLM-scoring (structured-llm-score): drie-tier parse structured → regex → score-0.

Backends die `StructuredLLMProvider` vervullen leveren gegarandeerd-parseerbare JSON; de regex blijft
de geteste fallback. `final` blijft de cosine (converge-ranking) — score raakt 'm niet aan.
"""

import json

from zeef.drivers.local import HashingEmbed, LexicalReranker
from zeef.models import Criteria, Criterion, Document
from zeef.pipeline.score import score
from zeef.profiles import ProviderBundle
from zeef.protocols import StructuredLLMProvider


class PlainFakeLLM:
    """Alleen `complete()` — vervult NIET `StructuredLLMProvider`."""

    name, location = "fake-plain", "local"

    def __init__(self, text="SCORE: 70\nMOTIVATIE: regex-pad"):
        self._text = text
        self.text_calls = []

    def complete(self, prompt, *, system=None):
        self.text_calls.append(prompt)
        return self._text


class StructuredFakeLLM:
    """Heeft `complete_json` én `complete` — vervult `StructuredLLMProvider`."""

    name, location = "fake-structured", "local"

    def __init__(self, obj, *, text="SCORE: 0\nMOTIVATIE: regex-fallback"):
        self._obj = obj
        self._text = text
        self.json_calls = []
        self.text_calls = []

    def complete_json(self, prompt, schema, *, system=None):
        self.json_calls.append((prompt, schema))
        return self._obj

    def complete(self, prompt, *, system=None):
        self.text_calls.append(prompt)
        return self._text


def _docs(n):
    out = []
    for i in range(n):
        d = Document(id=f"d{i:02d}", source_path=f"/d{i}", doc_type="email", text=f"tekst {i}")
        d.scores["final"] = 1.0 - i * 0.01
        out.append(d)
    return out


def _criteria():
    return Criteria(query="q", items=[Criterion(label="publicatieclausule", description="x")], source="llm")


def _bundle(llm):
    return ProviderBundle(llm=llm, embed=HashingEmbed(), reranker=LexicalReranker(), no_llm=False)


def _events(audit):
    return [json.loads(line) for line in audit.path.read_text(encoding="utf-8").splitlines()]


def _llm_score_event(audit):
    return [e for e in _events(audit) if e["action"] == "llm-score"][0]


def test_capability_protocol_distinguishes_backends():
    # 4.2/4.1: alleen de backend mét complete_json vervult het protocol.
    assert isinstance(StructuredFakeLLM({"score": 1, "motivatie": "x"}), StructuredLLMProvider)
    assert not isinstance(PlainFakeLLM(), StructuredLLMProvider)


def test_structured_path_sets_relevance_and_logs_schema(audit):
    # 4.1/3.1/3.5: structured-pad gebruikt JSON; audit logt route + schema + raw_structured.
    llm = StructuredFakeLLM({"score": 80, "motivatie": "raakt de publicatieclausule"})
    docs = _docs(1)
    score(docs, _criteria(), _bundle(llm), audit, "q", top_k=0)
    assert docs[0].scores["llm_relevance"] == 0.8
    assert docs[0].rationale == "raakt de publicatieclausule"
    assert docs[0].scores["final"] == 1.0  # cosine onaangeroerd
    assert llm.json_calls and not llm.text_calls  # structured-pad, geen regex-call
    evt = _llm_score_event(audit)
    assert evt["inputs"]["route"] == "structured"
    assert evt["inputs"]["schema"]["required"] == ["score", "motivatie"]
    assert evt["inputs"]["raw_structured"] == {"score": 80, "motivatie": "raakt de publicatieclausule"}


def test_complete_json_none_falls_back_to_regex(audit):
    # 4.3: complete_json → None ⇒ regex-fallback via complete().
    llm = StructuredFakeLLM(None, text="SCORE: 40\nMOTIVATIE: deels relevant")
    docs = _docs(1)
    score(docs, _criteria(), _bundle(llm), audit, "q", top_k=0)
    assert docs[0].scores["llm_relevance"] == 0.4
    assert docs[0].rationale == "deels relevant"
    assert llm.json_calls and llm.text_calls  # structured geprobeerd, daarna regex
    evt = _llm_score_event(audit)
    assert evt["inputs"]["route"] == "regex" and "schema" not in evt["inputs"]


def test_complete_json_invalid_dict_falls_back_to_regex(audit):
    # 4.3: ontbrekende velden in het object ⇒ regex-fallback.
    llm = StructuredFakeLLM({"oops": 1}, text="SCORE: 55\nMOTIVATIE: x")
    docs = _docs(1)
    score(docs, _criteria(), _bundle(llm), audit, "q", top_k=0)
    assert docs[0].scores["llm_relevance"] == 0.55
    assert _llm_score_event(audit)["inputs"]["route"] == "regex"


def test_complete_json_raising_falls_back_to_regex(audit):
    # 4.3: een werpende complete_json wordt opgevangen ⇒ regex-fallback, geen crash.
    class Raiser(StructuredFakeLLM):
        def complete_json(self, prompt, schema, *, system=None):
            raise RuntimeError("boom")

    llm = Raiser(None, text="SCORE: 30\nMOTIVATIE: x")
    docs = _docs(1)
    score(docs, _criteria(), _bundle(llm), audit, "q", top_k=0)
    assert docs[0].scores["llm_relevance"] == 0.3
    assert _llm_score_event(audit)["inputs"]["route"] == "regex"


def test_both_paths_unparseable_scores_zero_relevance(audit):
    # 4.4: structured faalt én regex vindt geen score ⇒ llm_relevance 0.0, ruwe tekst bewaard.
    llm = StructuredFakeLLM(None, text="ik weet het niet")
    docs = _docs(1)
    score(docs, _criteria(), _bundle(llm), audit, "q", top_k=0)
    assert docs[0].scores["llm_relevance"] == 0.0
    assert docs[0].rationale == "ik weet het niet"
    assert docs[0].scores["final"] == 1.0  # geen demotion
