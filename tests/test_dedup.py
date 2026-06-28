"""Dedup (relate-spec): `overlaps-with`-band vs `duplicate-of`.

Scharnierend paar: één kandidaatpaar met cosine net ónder de near-dup-drempel → `overlaps-with`;
één op/boven de drempel → `duplicate-of`. Bewijst dat de drempel het onderscheid maakt en dat
`overlaps-with` (voorheen een dood contract) nu echt wordt uitgestoten.
"""

import math

from zeef.models import Document
from zeef.pipeline import dedup
from zeef.pipeline.dedup import link_near_duplicates


class FakeEmbed:
    """Controleerbare embeddings per tekst → exacte cosine in/onder de band, los van de tekst."""

    name, location = "fake-embed", "local"

    def __init__(self, vecs):
        self._vecs = vecs

    def embed(self, texts, *, progress=None):
        return [self._vecs[t] for t in texts]


def _unit(deg):
    r = math.radians(deg)
    return [math.cos(r), math.sin(r)]


def test_overlap_band_vs_duplicate(audit, monkeypatch):
    a = Document(id="a", source_path="/a", doc_type="pdf_digital", text="ta")
    b = Document(id="b", source_path="/b", doc_type="pdf_digital", text="tb")
    c = Document(id="c", source_path="/c", doc_type="pdf_digital", text="tc")
    d = Document(id="d", source_path="/d", doc_type="pdf_digital", text="td")
    # cos(37°)≈0.80 → in de band [0.7, 0.9); cos(8°)≈0.99 → op/boven near-dup 0.9.
    vecs = {"ta": _unit(0), "tb": _unit(37), "tc": _unit(0), "td": _unit(8)}
    monkeypatch.setattr(dedup, "_minhash_candidate_pairs", lambda docs: [(a, b), (c, d)])

    link_near_duplicates([a, b, c, d], FakeEmbed(vecs), audit, threshold=0.9, overlap_threshold=0.7)

    # paar (a,b): partiële overlap → overlaps-with (op de niet-representant b → rep a), geen duplicaat
    assert any(r.kind == "overlaps-with" and r.target_id == "a" for r in b.relations)
    assert not any(r.kind == "duplicate-of" for r in a.relations + b.relations)
    # paar (c,d): boven near-dup → duplicate-of (d → c), geen overlap
    assert any(r.kind == "duplicate-of" and r.target_id == "c" for r in d.relations)
    assert not any(r.kind == "overlaps-with" for r in c.relations + d.relations)
    # evidence draagt de cosine-waarde
    overlap = next(r for r in b.relations if r.kind == "overlaps-with")
    assert "cosine" in overlap.evidence
