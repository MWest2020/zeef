"""Criteria-articulatie (criteria-spec): LLM leidt benoemde criteria af; --no-llm valt terug."""

import json

from zeef.config import ProfileName, Settings
from zeef.drivers.local import HashingEmbed, LexicalReranker
from zeef.pipeline.criteria import articulate_criteria
from zeef.profiles import ProviderBundle


class FakeLLM:
    name = "fake-llm"
    location = "local"

    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def complete(self, prompt, *, system=None):
        self.calls.append(prompt)
        return self.answer


def _bundle(llm, no_llm):
    return ProviderBundle(llm=llm, embed=HashingEmbed(), reranker=LexicalReranker(), no_llm=no_llm)


def _events(audit):
    return [json.loads(line) for line in audit.path.read_text(encoding="utf-8").splitlines()]


def test_llm_articulates_named_criteria_and_logs_prompt(audit):
    answer = (
        "Publicatieclausule: het document bevat afspraken over openbaarmaking\n"
        "Geheimhouding: er is sprake van een geheimhoudingsclausule\n"
        "- Partijen: de genoemde partijen komen voor\n"
    )
    fake = FakeLLM(answer)
    crit = articulate_criteria("openbaarmaking afspraken tussen partijen", _bundle(fake, no_llm=False), audit)
    assert crit.source == "llm"
    assert [c.label for c in crit.items] == ["Publicatieclausule", "Geheimhouding", "Partijen"]
    assert crit.items[0].description.startswith("het document")
    evt = [e for e in _events(audit) if e["action"] == "articulate"][0]
    assert evt["prompt"] and evt["model"] == "fake-llm"


def test_unparseable_answer_falls_back(audit):
    fake = FakeLLM("ik kan hier geen criteria van maken")
    crit = articulate_criteria("zoekvraag x", _bundle(fake, no_llm=False), audit)
    assert crit.source == "fallback"
    assert len(crit.items) == 1 and crit.items[0].description == "zoekvraag x"


def test_no_llm_falls_back_without_calling_llm(audit):
    fake = FakeLLM("ONGEBRUIKT")
    crit = articulate_criteria("begroting subsidie cultuur 2026", _bundle(fake, no_llm=True), audit)
    assert crit.source == "fallback"
    assert len(crit.items) == 1
    assert crit.items[0].description == "begroting subsidie cultuur 2026"
    assert fake.calls == []  # geen enkele LLM-call onder --no-llm
    assert [e for e in _events(audit) if e["action"] == "fallback"]


def test_default_settings_top_k_is_bounded():
    assert Settings(_env_file=None).llm_score_top_k == 250
    # Profielresolutie blijft werken; criteria gebruikt alleen providers.llm.
    assert ProfileName.sovereign.value == "sovereign"
