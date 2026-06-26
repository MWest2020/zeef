"""Converge-ranking invarianten (D14/D16/D20/D22/D23): de passage-cosine is de enige, auditbare
selector; geen verborgen recall-gate; duplicaat-collapse ná ranking; deterministische "why".

Dekt taken 7.1, 7.3, 7.4, 7.5, 7.7, 7.8, 7.9. Taak 7.2 (selectie vast vóór UI) en 7.6 (assen
gescheiden) worden gedekt door test_e2e resp. test_scope_filter.
"""

import json

from zeef.config import CutoffMode
from zeef.drivers.local import HashingEmbed, LexicalReranker
from zeef.export import build_report_data
from zeef.models import Criteria, Criterion, Document
from zeef.pipeline.rerank import rerank
from zeef.pipeline.retrieve import retrieve
from zeef.pipeline.score import score
from zeef.pipeline.select import select
from zeef.profiles import ProviderBundle
from zeef.similarity import term_overlap


class FakeLLM:
    name, location = "fake-llm", "local"

    def complete(self, prompt, *, system=None):
        return "SCORE: 50\nMOTIVATIE: raakt een criterium"


def _doc(doc_id, text, path=None):
    return Document(id=doc_id, source_path=path or f"/{doc_id}", doc_type="other", text=text)


def _criteria():
    return Criteria(query="q", items=[Criterion(label="x", description="y")], source="llm")


def _bundle(llm, no_llm):
    return ProviderBundle(llm=llm, embed=HashingEmbed(), reranker=LexicalReranker(), no_llm=no_llm)


def _events(audit):
    return [json.loads(line) for line in audit.path.read_text(encoding="utf-8").splitlines()]


def test_final_is_passage_cosine_and_no_stage_demotes(audit):
    """7.8/7.4/1.2-1.4: retrieve zet final=cosine; rerank/score raken final niet aan; geen demotion."""
    q = "begroting subsidie cultuur"
    docs = [_doc("hit", "begroting subsidie cultuur 2026"), _doc("miss", "begroting maar verder anders")]
    cands = retrieve(docs, HashingEmbed(), audit, q)
    for d in cands:
        assert d.scores["final"] == d.scores["embed_sim"]  # cosine is de selector

    ordered = rerank(cands, LexicalReranker(), audit, q)
    for d in ordered:
        assert "rerank" in d.scores  # side-score wél gezet
        assert d.scores["final"] == d.scores["embed_sim"]  # rerank raakt final niet aan

    score(ordered, _criteria(), _bundle(FakeLLM(), no_llm=False), audit, q, top_k=1)
    miss = next(d for d in ordered if d.id == "miss")
    # de niet-gescoorde kandidaat is NIET gedemoveerd naar 0.0: final blijft de cosine.
    assert miss.scores["final"] == miss.scores["embed_sim"]
    assert "llm_relevance" not in miss.scores


def test_relevance_uses_best_matching_passage_not_average(audit):
    """7.9: een document dat maar in één passage relevant is, rankt op die passage (max-chunk)."""
    noise = "asdf qwer zxcv plif knor " * 40
    relevant = " begroting subsidie cultuur 2026 "
    hit = _doc("hit", noise + relevant + noise)
    miss = _doc("miss", noise + noise)
    retrieve([hit, miss], HashingEmbed(), audit, "begroting subsidie cultuur 2026", chunk_size=80)
    assert hit.scores["final"] > miss.scores["final"]
    assert term_overlap("begroting subsidie cultuur", hit.best_passage)  # de passage draagt de match


def test_duplicate_group_collapses_to_highest_ranked_after_ranking(audit):
    """7.5: collapse ná ranking — hoogste final is representant; rest out_of_scope + relatie + log."""
    rep_relate = _doc("a", "zelfde inhoud", path="/a")          # relate's rep (laagste bronpad)
    higher = _doc("b", "zelfde inhoud", path="/b")
    higher.add_relation("duplicate-of", "a", evidence="test")    # niet-rep wijst naar rep
    rep_relate.scores["final"] = 0.50
    higher.scores["final"] = 0.90                                # maar b rankt hoger

    selected = select([rep_relate, higher], CutoffMode.top_n, 10, audit)

    assert [d.id for d in selected] == ["b"]                     # hoogst gerangschikt = representant
    assert higher.decision == "selected"
    assert rep_relate.decision == "out_of_scope"                 # gecollapst
    assert "duplicaat van representant b" in rep_relate.decision_reason
    assert any(r.kind == "duplicate-of" and r.target_id == "a" for r in higher.relations)  # edge blijft
    excl = [e for e in _events(audit)
            if e["action"] == "excluded" and e["document_ids"] == ["a"]]
    assert excl and excl[0]["inputs"].get("reason")


def test_exact_duplicate_tiebreak_is_query_independent(audit):
    """7.5: bij gelijke final (exacte duplicaten) wint de laagste bronpad — query-onafhankelijk."""
    a = _doc("a", "x", path="/a")
    b = _doc("b", "x", path="/b")
    b.add_relation("duplicate-of", "a", evidence="test")
    a.scores["final"] = b.scores["final"] = 0.7
    selected = select([a, b], CutoffMode.top_n, 10, audit)
    assert [d.id for d in selected] == ["a"]                     # /a < /b → a representant
    assert b.decision == "out_of_scope"


def test_cluster_membership_does_not_filter_selection(audit):
    """7.3/7.4: een 'Overig'-document met hoge relevantie wordt gewoon geselecteerd; geen score-mix."""
    high = _doc("hi", "x")
    high.scores["final"] = 0.95
    high.topic = "Overig"
    low = _doc("lo", "y")
    low.scores["final"] = 0.10
    low.topic = "Begroting"
    selected = select([high, low], CutoffMode.top_n, 1, audit)
    assert [d.id for d in selected] == ["hi"]                    # relevantie beslist, niet het cluster


def test_ranking_is_deterministic(audit):
    """7.1: zelfde corpus + query + model → identieke scores en ordening."""
    def run():
        docs = [_doc("a", "begroting cultuur"), _doc("b", "totaal ander onderwerp")]
        return {d.id: d.scores["final"] for d in retrieve(docs, HashingEmbed(), audit, "begroting cultuur")}
    assert run() == run()


def test_report_carries_query_and_deterministic_why(audit):
    """7.7: report-meta draagt de query; per document een deterministische 'why' (passage + termen)."""
    d = _doc("d", "begroting subsidie cultuur")
    d.scores["final"] = 0.8
    d.best_passage = "de begroting voor subsidie cultuur 2026"
    d.decision = "selected"
    data = build_report_data("begroting cultuur", "2026-01-01T00:00:00", [d], {}, [d])
    assert data["query"] == "begroting cultuur"
    doc = data["documents"]["d"]
    assert doc["why_passage"].startswith("de begroting")
    assert "begroting" in doc["why_terms"] and "cultuur" in doc["why_terms"]
    assert doc["score"] == 0.8
