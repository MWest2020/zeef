"""Hardening van de discover-route: de chunk-cap bemonstert gelijkmatig (niet de staart droppen),
en de clustering-randgevallen (leeg corpus, één document, nulvector-document) gedragen zich
deterministisch — een nulvector-document valt naar "Overig" i.p.v. de clustering te laten crashen."""

from zeef.audit import AuditLog
from zeef.config import ProfileName, Settings
from zeef.drivers.local import HashingEmbed
from zeef.models import Chunk, Document
from zeef.pipeline.retrieve import embed_chunks
from zeef.pipeline.topics import cluster_topics
from zeef.profiles import resolve_providers

_CUT = {"onderwerp_distance": 0.5, "deelonderwerp_distance": 0.42, "max_chunks_per_doc": 6}


def _providers():
    return resolve_providers(ProfileName.sovereign, no_llm=True, settings=Settings(_env_file=None))


def _doc(i: int, text: str) -> Document:
    return Document(id=f"d{i}", source_path=f"/x/{i}.txt", doc_type="other", text=text)


def test_max_chunks_cap_even_samples(tmp_path):
    long_text = " ".join(f"woord{i}" for i in range(4000))  # ruim meer dan 6 chunks van 1000 tekens
    doc = _doc(1, long_text)
    audit = AuditLog(tmp_path / "a.jsonl")
    embed_chunks([doc], HashingEmbed(), audit, max_chunks_per_doc=3)
    assert len(doc.chunks) == 3                                  # gecapt op 3
    # determinisme: identieke run geeft identieke chunk-selectie
    doc2 = _doc(1, long_text)
    embed_chunks([doc2], HashingEmbed(), AuditLog(tmp_path / "b.jsonl"), max_chunks_per_doc=3)
    assert [c.text for c in doc.chunks] == [c.text for c in doc2.chunks]


def test_empty_corpus_yields_no_topics(tmp_path):
    out = cluster_topics([], _providers(), AuditLog(tmp_path / "a.jsonl"),
                         min_cluster_size=5, **_CUT)
    assert out["onderwerpen"] == []                              # geen crash, lege landkaart


def test_single_document_is_trivially_grouped(tmp_path):
    doc = _doc(1, "een document over de omgevingsvergunning aan de straatweg")
    embed_chunks([doc], HashingEmbed(), AuditLog(tmp_path / "e.jsonl"), max_chunks_per_doc=6)
    out = cluster_topics([doc], _providers(), AuditLog(tmp_path / "a.jsonl"),
                         min_cluster_size=1, **_CUT)
    placed = [i for o in out["onderwerpen"] for d in o["deelonderwerpen"] for i in d["doc_ids"]]
    assert placed == ["d1"]                                     # het ene doc is geplaatst


def test_zero_vector_document_routed_to_overig(tmp_path):
    # Drie normale docs + één met een pure nulvector-chunk (onbruikbaar voor cosine).
    docs = [_doc(i, f"omgevingsvergunning perceel straatweg variant {i}") for i in range(3)]
    embed_chunks(docs, HashingEmbed(), AuditLog(tmp_path / "e.jsonl"), max_chunks_per_doc=6)
    zero = _doc(99, "x")
    zero.chunks = [Chunk(id="z0", ordinal=0, text="x", embedding=[0.0] * 8)]
    out = cluster_topics(docs + [zero], _providers(), AuditLog(tmp_path / "a.jsonl"),
                         min_cluster_size=1, **_CUT)
    overig = [o for o in out["onderwerpen"] if o["label"] == "Overig"]
    assert overig, "nulvector-document hoort een Overig-bak te maken"
    assert "d99" in [i for d in overig[0]["deelonderwerpen"] for i in d["doc_ids"]]
