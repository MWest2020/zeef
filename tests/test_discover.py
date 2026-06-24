"""Discover-mode (discover-spec): query-loze onderwerp-landkaart over het volledige corpus.

Bewijst: (a) ontdekken zonder query — geen query-gedreven stages; (b) determinisme; (c) `--no-llm`
levert TF-IDF-labels, geen samenvattingen, geen model-call; (d) samenvatting per cluster (op
representanten), niet per document; (e) manifest met clustering-parameters + embedding-bron;
(f) een offline, self-contained `report.html`.
"""

import json

from zeef.audit import AuditLog
from zeef.config import ProfileName, Settings
from zeef.drivers.local import HashingEmbed, LexicalReranker
from zeef.pipeline.discover import run_discover
from zeef.profiles import ProviderBundle, resolve_providers


class SpyLLM:
    name, location = "spy-llm", "local"

    def __init__(self):
        self.calls = []

    def complete(self, prompt, *, system=None):
        self.calls.append(prompt)
        return "Een onderwerp"


def _events(audit):
    return [json.loads(line) for line in audit.path.read_text(encoding="utf-8").splitlines()]


def _stages(audit):
    return {e["stage"] for e in _events(audit)}


def _sovereign(no_llm=True):
    return resolve_providers(ProfileName.sovereign, no_llm=no_llm, settings=Settings(_env_file=None))


def _run(corpus, out_dir, providers, **kw):
    audit = AuditLog(out_dir / "audit.jsonl")
    return run_discover(corpus, providers, out_dir, audit, **kw), audit


def test_discover_builds_nested_map_without_query_stages(corpus, tmp_path):
    result, audit = _run(corpus, tmp_path, _sovereign())
    onderwerpen = result.landkaart["onderwerpen"]
    assert onderwerpen  # niet-leeg (minstens een groep / "Overig")
    # genest: elk onderwerp heeft deelonderwerpen met doc_ids
    assert all(o["deelonderwerpen"] and all("doc_ids" in d for d in o["deelonderwerpen"])
               for o in onderwerpen)
    # géén query-gedreven stages uitgevoerd
    stages = _stages(audit)
    assert {"ingest", "validity", "relate", "embed", "topics", "export"} <= stages
    assert not ({"criteria", "retrieve", "rerank", "score", "select"} & stages)


def test_discover_is_deterministic(corpus, tmp_path):
    a, _ = _run(corpus, tmp_path / "a", _sovereign())
    b, _ = _run(corpus, tmp_path / "b", _sovereign())
    # identieke landkaart (op de timestamp na, die we niet vergelijken)
    assert a.landkaart["onderwerpen"] == b.landkaart["onderwerpen"]
    assert a.landkaart["documents"] == b.landkaart["documents"]


def test_no_llm_tfidf_labels_no_summary_no_call(corpus, tmp_path):
    result, audit = _run(corpus, tmp_path, _sovereign(no_llm=True))
    assert result.landkaart["source"] == "fallback"
    # geen samenvattingen
    assert all(d.get("summary", "") == "" for o in result.landkaart["onderwerpen"]
               for d in o["deelonderwerpen"])
    # geen enkele model-call (NullLLM zou hard falen als-ie geraakt werd; én geen label/summary-events)
    actions = {e["action"] for e in _events(audit)}
    assert "cluster-summary" not in actions and "label" not in actions


def test_cluster_summary_on_representatives_not_per_document(corpus, tmp_path):
    spy = SpyLLM()
    providers = ProviderBundle(llm=spy, embed=HashingEmbed(), reranker=LexicalReranker(), no_llm=False)
    result, audit = _run(corpus, tmp_path, providers)
    actions = [e["action"] for e in _events(audit)]
    assert "cluster-summary" in actions          # per cluster gesamenvat
    assert "summary" not in actions               # NIET de per-document summarise
    # de LLM raakt labels + cluster-samenvattingen, niet elk document
    n_docs = len(result.landkaart["documents"])
    assert 0 < len(spy.calls) < max(2, n_docs)


def test_manifest_records_params_and_embed_source(corpus, tmp_path):
    result, _ = _run(corpus, tmp_path, _sovereign(), max_chunks_per_doc=8, min_cluster_size=2)
    params = result.manifest["params"]
    assert params["embed_source"] == "hashing-embed-v1"
    assert params["min_cluster_size"] == 2 and params["max_chunks_per_doc"] == 8
    assert "onderwerp_distance" in params and "deelonderwerp_distance" in params


def test_report_html_is_offline_self_contained(corpus, tmp_path):
    _run(corpus, tmp_path, _sovereign())
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert (tmp_path / "discover-map.json").exists()
    for forbidden in ("http://", "https://", "fetch(", "XMLHttpRequest", "<script src", "<link "):
        assert forbidden not in html, forbidden
