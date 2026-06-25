"""Retrieve + rerank (retrieve-spec): scores vastgelegd, chunking, rerank herordent."""

from zeef.audit import AuditLog
from zeef.drivers.local import HashingEmbed, LexicalReranker
from zeef.models import Document
from zeef.pipeline.chunking import chunk_document
from zeef.pipeline.rerank import rerank
from zeef.pipeline.retrieve import retrieve


def _doc(doc_id: str, text: str) -> Document:
    return Document(id=doc_id, source_path=f"/{doc_id}", doc_type="other", text=text)


def test_long_document_is_chunked(tmp_path):
    doc = _doc("d", "x" * 2500)
    chunks = chunk_document(doc, chunk_size=1000)
    assert [c.ordinal for c in chunks] == [0, 1, 2]
    assert chunks[0].id == "d:0"
    assert "".join(c.text for c in chunks) == doc.text


def test_chunking_is_deterministic():
    a = chunk_document(_doc("d", "abc def " * 100), 50)
    b = chunk_document(_doc("d", "abc def " * 100), 50)
    assert [c.text for c in a] == [c.text for c in b]


def test_candidates_get_embed_sim(tmp_path):
    audit = AuditLog(tmp_path / "a.jsonl")
    docs = [_doc("a", "begroting subsidie cultuur"), _doc("b", "iets heel anders over fietsen")]
    cands = retrieve(docs, HashingEmbed(), audit, "begroting subsidie cultuur")
    assert all("embed_sim" in d.scores for d in cands)
    # Het relevante document scoort hoger op de eerste pass.
    assert docs[0].scores["embed_sim"] > docs[1].scores["embed_sim"]


def test_rerank_records_side_score_without_overriding_cosine(tmp_path):
    audit = AuditLog(tmp_path / "a.jsonl")
    # Geconstrueerd zodat embed (TF-concentratie) en BM25 (distincte querytermen) verschillen.
    d1 = _doc("d1", "beta beta beta beta beta")
    d2 = _doc("d2", "beta gamma delta epsilon zeta eta theta iota kappa lambda")
    query = "beta gamma"
    cands = retrieve([d1, d2], HashingEmbed(), audit, query)
    embed_order = [d.id for d in sorted(cands, key=lambda d: d.scores["embed_sim"], reverse=True)]
    ordered = rerank(cands, LexicalReranker(), audit, query)
    # rerank legt zijn score als side-score vast maar schrijft `final` NIET en herordent niet:
    assert all("rerank" in d.scores for d in ordered)
    assert all(d.scores["final"] == d.scores["embed_sim"] for d in ordered)  # final = cosine
    assert [d.id for d in ordered] == embed_order   # cosine-volgorde behouden, geen reorder/gate


def test_excluded_docs_are_not_candidates(tmp_path):
    audit = AuditLog(tmp_path / "a.jsonl")
    keep = _doc("keep", "begroting cultuur")
    drop = _doc("drop", "begroting cultuur")
    drop.decision = "out_of_scope"
    drop.decision_reason = "test"
    cands = retrieve([keep, drop], HashingEmbed(), audit, "begroting")
    assert [d.id for d in cands] == ["keep"]
