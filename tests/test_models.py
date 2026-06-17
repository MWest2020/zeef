"""Rooktests voor het canonieke datamodel (acceptatie: reproduceerbare id, relaties)."""

from zeef.models import Document, content_id


def test_content_id_is_reproducible():
    a = content_id("hallo wereld", "/docs/a.eml")
    b = content_id("hallo wereld", "/docs/a.eml")
    assert a == b


def test_content_id_differs_on_source_path():
    a = content_id("zelfde tekst", "/docs/a.eml")
    b = content_id("zelfde tekst", "/docs/b.eml")
    assert a != b


def test_add_relation_is_idempotent():
    doc = Document(id="x", source_path="/docs/a.eml", doc_type="email")
    doc.add_relation("duplicate-of", "y", evidence="hash-match")
    doc.add_relation("duplicate-of", "y", evidence="hash-match")
    assert len(doc.relations) == 1
    assert doc.relations[0].evidence == "hash-match"
