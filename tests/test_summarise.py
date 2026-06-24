"""Summarise (summarise-spec): ≤N-woord inhoudssamenvatting met LLM; `--no-llm` = geen call.

Bewijst expliciet: (a) met LLM → `metadata["summary"]` gevuld + prompt/model/locatie gelogd, los
van `rationale`; (b) onder `--no-llm` → geen samenvatting én geen enkele model-call.
"""

import json

from zeef.drivers.local import HashingEmbed, LexicalReranker
from zeef.models import Document
from zeef.pipeline.summarise import summarise
from zeef.profiles import ProviderBundle


class SpyLLM:
    name, location = "spy-llm", "local"

    def __init__(self, text="Dit document beschrijft het subsidiebesluit cultuur 2026."):
        self.calls = []
        self._text = text

    def complete(self, prompt, *, system=None):
        self.calls.append(prompt)
        return self._text


def _docs(n=2):
    out = []
    for i in range(n):
        d = Document(id=f"d{i}", source_path=f"/d{i}", doc_type="pdf_digital", text=f"inhoud {i} " * 50)
        d.decision = "selected"
        out.append(d)
    return out


def _bundle(no_llm, llm=None):
    return ProviderBundle(llm=llm or SpyLLM(), embed=HashingEmbed(),
                          reranker=LexicalReranker(), no_llm=no_llm)


def _events(audit):
    return [json.loads(line) for line in audit.path.read_text(encoding="utf-8").splitlines()]


def test_summarise_sets_summary_and_logs_prompt(audit):
    docs = _docs(2)
    spy = SpyLLM()
    summarise(docs, _bundle(no_llm=False, llm=spy), audit, max_words=100)
    assert all(d.metadata.get("summary") for d in docs)  # gevuld
    assert all(d.rationale == "" for d in docs)  # los van de motivatie
    assert len(spy.calls) == 2
    evs = [e for e in _events(audit) if e["action"] == "summary"]
    assert len(evs) == 2
    assert all(e["prompt"] and e["model"] == "spy-llm" and e["location"] == "local" for e in evs)


def test_summary_respects_max_words(audit):
    long = " ".join(f"woord{i}" for i in range(300))
    docs = _docs(1)
    summarise(docs, _bundle(no_llm=False, llm=SpyLLM(text=long)), audit, max_words=100)
    assert len(docs[0].metadata["summary"].split()) == 100


def test_no_llm_makes_no_call_and_no_summary(audit):
    docs = _docs(2)
    spy = SpyLLM()
    summarise(docs, _bundle(no_llm=True, llm=spy), audit, max_words=100)
    assert spy.calls == []  # geen enkele model-call
    assert all("summary" not in d.metadata for d in docs)
