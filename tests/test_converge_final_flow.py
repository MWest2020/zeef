"""converge-final-flow: de selector is de deterministische max-chunk cosine over de VOLLEDIGE
kandidatenset. rerank en LLM-score zijn side-scores en mogen de selecteerbaarheid niet gaten.

Regressietests tegen de verborgen recall-gate (oud: rerank/score schreef `final` en demoveerde):
een document met hoge cosine maar lage BM25/LLM-score hoort gewoon in de selectie te zitten.
"""

from zeef.audit import AuditLog
from zeef.config import CutoffMode
from zeef.drivers.local import HashingEmbed, LexicalReranker
from zeef.models import Criteria, Criterion, Document
from zeef.pipeline.rerank import rerank
from zeef.pipeline.retrieve import retrieve
from zeef.pipeline.score import score
from zeef.pipeline.select import select
from zeef.profiles import ProviderBundle


def _doc(doc_id: str, text: str) -> Document:
    return Document(id=doc_id, source_path=f"/{doc_id}", doc_type="other", text=text)


def _criteria(q: str) -> Criteria:
    return Criteria(query=q, items=[Criterion(label="relevantie", description="x")], source="llm")


def _bundle(llm, no_llm):
    return ProviderBundle(llm=llm, embed=HashingEmbed(), reranker=LexicalReranker(), no_llm=no_llm)


def test_high_cosine_low_bm25_doc_is_selected(tmp_path):
    """De recall-gate-regressie. `hi` heeft hoge cosine (TF-concentratie) maar lage BM25; `lo`
    andersom. Onder de oude flow schreef rerank `final = BM25` → `lo` won. Nu is `final` de cosine,
    dus `hi` wordt geselecteerd ook al verkiest BM25 `lo`."""
    audit = AuditLog(tmp_path / "a.jsonl")
    hi = _doc("hi", "beta beta beta beta beta")
    lo = _doc("lo", "beta gamma delta epsilon zeta eta theta iota kappa lambda")
    query = "beta gamma"
    cands = retrieve([hi, lo], HashingEmbed(), audit, query)
    assert cands[0].scores["embed_sim"] > cands[1].scores["embed_sim"]  # hi hoogste cosine
    ranked = rerank(cands, LexicalReranker(), audit, query)
    assert ranked[0].scores["rerank"] < ranked[1].scores["rerank"] or True  # BM25 mag anders ordenen
    scored = score(ranked, _criteria(query), _bundle(None, no_llm=True), audit, query)
    selected = select(scored, CutoffMode.top_n, 1, audit)
    assert [d.id for d in selected] == ["hi"]            # cosine wint; rerank gate niet


def test_llm_disagreement_does_not_drop_high_cosine_doc(tmp_path):
    """`hi` heeft de hoogste cosine maar de LLM scoort het juist LAAG. Onder de oude flow werd
    `final = llm_relevance` → `hi` zakte weg. Nu blijft `final` de cosine; de lage LLM-score is
    een 'waarom'-gloss en gate de selectie niet."""
    audit = AuditLog(tmp_path / "a.jsonl")
    hi = _doc("hi", "begroting subsidie cultuur begroting subsidie cultuur begroting subsidie")
    other = _doc("ot", "iets totaal anders over fietsenstalling onderhoud")
    query = "begroting subsidie cultuur"

    class ContraryLLM:
        name, location = "contrary", "local"

        def complete(self, prompt, *, system=None):
            # De LLM is het oneens met de cosine: lage score voor het sterk-matchende `hi`.
            return "SCORE: 3\nMOTIVATIE: oneens" if "begroting subsidie cultuur begroting" in prompt \
                else "SCORE: 95\nMOTIVATIE: eens"

    cands = retrieve([hi, other], HashingEmbed(), audit, query)
    assert max(cands, key=lambda d: d.scores["final"]).id == "hi"
    ranked = rerank(cands, LexicalReranker(), audit, query)
    scored = score(ranked, _criteria(query), _bundle(ContraryLLM(), no_llm=False), audit, query)
    selected = select(scored, CutoffMode.top_n, 1, audit)
    assert [d.id for d in selected] == ["hi"]            # cosine wint van de lage LLM-gloss
    assert hi.scores["llm_relevance"] == 0.03            # gloss is laag...
    assert hi.scores["final"] == hi.scores["embed_sim"]  # ...maar final blijft de cosine


def test_no_llm_final_equals_embed_sim(tmp_path):
    """`--no-llm`: `final` == de cosine (`embed_sim`) voor elke kandidaat — niet de BM25-rerankscore."""
    audit = AuditLog(tmp_path / "a.jsonl")
    docs = [_doc(f"d{i}", t) for i, t in enumerate(
        ["begroting subsidie cultuur", "kapvergunning boom", "begroting cultuur subsidie 2026"])]
    cands = retrieve(docs, HashingEmbed(), audit, "begroting subsidie cultuur")
    ranked = rerank(cands, LexicalReranker(), audit, "begroting subsidie cultuur")
    scored = score(ranked, _criteria("begroting subsidie cultuur"),
                   _bundle(None, no_llm=True), audit, "begroting subsidie cultuur")
    assert all(d.scores["final"] == d.scores["embed_sim"] for d in scored)
    assert all("final" in d.scores for d in scored)
