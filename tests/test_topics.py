"""Topic-clustering (topic-clustering-spec): reproduceerbare groepering, deterministische labels.

Twee dingen worden expliciet bewezen, niet alleen geïmplementeerd:
- **Reproduceerbaarheid**: identieke embeddings + dezelfde gelogde parameters → identieke
  toewijzing (twee runs vergeleken), én de parameters staan in het run-manifest.
- **`--no-llm` maakt geen enkele model-call** en levert TF-IDF-fallbacklabels (`source: fallback`).
"""

import json

from zeef.audit import AuditLog
from zeef.config import CutoffMode, ProfileName, Settings
from zeef.drivers.local import HashingEmbed, LexicalReranker
from zeef.models import Chunk, Document
from zeef.pipeline.run import run_converge
from zeef.pipeline.topics import OVERIG, cluster_topics
from zeef.profiles import ProviderBundle, resolve_providers

# Drie strak gescheiden groepen: A (3×), B (3×) en één uitbijter C — bij min_cluster_size=3
# collapst C naar "Overig". Embeddings staan vast op de chunks → geen embed-call nodig.
_A, _B, _C = [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]


class SpyLLM:
    """Registreert elke aanroep en geeft een vast label terug; mag onder --no-llm niet geraakt."""

    name, location = "spy-llm", "local"

    def __init__(self):
        self.calls = []

    def complete(self, prompt, *, system=None):
        self.calls.append(prompt)
        return "Cultuurbeleid"


def _events(audit):
    return [json.loads(line) for line in audit.path.read_text(encoding="utf-8").splitlines()]


def _doc(i, vec, text):
    return _multichunk_doc(i, [vec], text)


def _multichunk_doc(i, vecs, text):
    d = Document(id=f"d{i:02d}", source_path=f"/d{i}", doc_type="pdf_digital", text=text)
    d.chunks = [Chunk(id=f"d{i:02d}#{j}", ordinal=j, text=text, embedding=v)
                for j, v in enumerate(vecs)]
    d.decision = "selected"
    return d


def _corpus():
    return [
        _doc(0, _A, "subsidie cultuur begroting theater"),
        _doc(1, _A, "subsidie cultuur begroting museum"),
        _doc(2, _A, "subsidie cultuur begroting dans"),
        _doc(3, _B, "vergunning bouw omgeving bestemmingsplan"),
        _doc(4, _B, "vergunning bouw omgeving aanvraag"),
        _doc(5, _B, "vergunning bouw omgeving sloop"),
        _doc(6, _C, "eenmalig procesbericht ontvangstbevestiging"),
    ]


def _bundle(no_llm, llm=None):
    return ProviderBundle(llm=llm or SpyLLM(), embed=HashingEmbed(),
                          reranker=LexicalReranker(), no_llm=no_llm)


def _assign(docs):
    return {d.id: (d.topic, d.subtopic) for d in docs}


_PARAMS = {"onderwerp_distance": 0.5, "deelonderwerp_distance": 0.2, "min_cluster_size": 3,
           "max_chunks_per_doc": 64}


def test_two_level_grouping_with_overig_collapse(audit):
    docs = _corpus()
    menu = cluster_topics(docs, _bundle(no_llm=True), audit, **_PARAMS)
    a = _assign(docs)
    # A-groep deelt één onderwerp; B-groep een ánder; de uitbijter valt in "Overig".
    assert a["d00"] == a["d01"] == a["d02"]
    assert a["d03"] == a["d04"] == a["d05"]
    assert a["d00"][0] != a["d03"][0]
    assert a["d06"] == (OVERIG, OVERIG)
    named = [o for o in menu["onderwerpen"] if o["label"] != OVERIG]
    assert len(named) == 2 and menu["source"] == "fallback"
    assert any(o["label"] == OVERIG for o in menu["onderwerpen"])


def test_reproducible_grouping_on_identical_embeddings(audit):
    first = _corpus()
    second = _corpus()
    cluster_topics(first, _bundle(no_llm=True), audit, **_PARAMS)
    cluster_topics(second, _bundle(no_llm=True), audit, **_PARAMS)
    # Identieke embeddings + dezelfde parameters → exact gelijke toewijzing (en labels).
    assert _assign(first) == _assign(second)


def test_no_llm_makes_no_model_call_and_labels_are_fallback(audit):
    docs = _corpus()
    spy = SpyLLM()
    menu = cluster_topics(docs, _bundle(no_llm=True, llm=spy), audit, **_PARAMS)
    assert spy.calls == []  # geen enkele model-call op de --no-llm-tak
    assert menu["source"] == "fallback"
    assert all(d.topic for d in docs)  # elk document heeft een (fallback)label


def test_manifest_records_clustering_params_and_topics_json(corpus, tmp_path):
    settings = Settings(_env_file=None)
    providers = resolve_providers(ProfileName.sovereign, no_llm=True, settings=settings)
    audit = AuditLog(tmp_path / "audit.jsonl")
    result = run_converge(corpus, "subsidie cultuur", providers, CutoffMode.target, 100,
                          tmp_path, audit, **_PARAMS)
    params = result.manifest["params"]
    assert params["onderwerp_distance"] == 0.5
    assert params["deelonderwerp_distance"] == 0.2
    assert params["min_cluster_size"] == 3
    assert params["max_chunks_per_doc"] == 64  # de cap is een clusterparameter, gelogd in het manifest
    assert (tmp_path / "topics.json").exists()


def test_two_runs_same_params_yield_identical_topics_json(corpus, tmp_path):
    settings = Settings(_env_file=None)
    out_a, out_b = tmp_path / "a", tmp_path / "b"
    for out in (out_a, out_b):
        providers = resolve_providers(ProfileName.sovereign, no_llm=True, settings=settings)
        run_converge(corpus, "subsidie cultuur", providers, CutoffMode.target, 100,
                     out, AuditLog(out / "audit.jsonl"), **_PARAMS)
    topics_a = json.loads((out_a / "topics.json").read_text(encoding="utf-8"))
    topics_b = json.loads((out_b / "topics.json").read_text(encoding="utf-8"))
    assert topics_a == topics_b and topics_a["onderwerpen"]


_SPLIT_PARAMS = {"onderwerp_distance": 0.5, "deelonderwerp_distance": 0.2, "min_cluster_size": 2,
                 "max_chunks_per_doc": 64}


def _split_corpus():
    # Twee strakke clusters; één document heeft 2 chunks in A en 1 in B → meerderheid A (T7).
    return [
        _doc(0, _A, "subsidie cultuur"),
        _doc(1, _A, "subsidie cultuur"),
        _doc(2, _B, "vergunning bouw"),
        _doc(3, _B, "vergunning bouw"),
        _multichunk_doc(9, [_A, _A, _B], "subsidie cultuur vergunning bouw"),
    ]


def test_document_with_chunks_in_two_clusters_gets_one_topic(audit):
    first, second = _split_corpus(), _split_corpus()
    cluster_topics(first, _bundle(no_llm=True), audit, **_SPLIT_PARAMS)
    cluster_topics(second, _bundle(no_llm=True), audit, **_SPLIT_PARAMS)
    split = first[-1]
    # Precies één onderwerp + één deelonderwerp, niet "Overig"...
    assert split.topic and split.subtopic and split.topic != OVERIG
    # ...en het is het meerderheidscluster (A, zoals d00), niet B (d02).
    assert split.topic == first[0].topic and split.subtopic == first[0].subtopic
    assert split.topic != first[2].topic
    # Deterministisch: twee runs op identieke embeddings geven dezelfde toewijzing.
    assert _assign(first) == _assign(second)


def test_llm_labelling_applies_label_and_logs_prompt(audit):
    docs = _corpus()
    spy = SpyLLM()
    menu = cluster_topics(docs, _bundle(no_llm=False, llm=spy), audit, **_PARAMS)
    assert menu["source"] == "llm"  # (b) bron is geen fallback meer
    assert spy.calls  # minstens één model-call op het LLM-pad
    # (a) het label belandt op de clusters (Overig blijft Overig, geen LLM-label)
    assert all(d.topic == "Cultuurbeleid" for d in docs if d.topic != OVERIG)
    # (c) per gelabeld cluster een audit-event met de exacte prompt, model en locatie
    evs = [e for e in _events(audit) if e["action"] == "label"]
    assert evs and all(e["prompt"] and e["model"] == "spy-llm" and e["location"] == "local"
                       for e in evs)


def test_empty_chunk_document_routes_to_overig_without_crashing(audit):
    # Spiegelbeeld van change 1's gelakt-test: een nul-embedding (bv. een gelakt/leeg document) mag
    # de cosine-clustering niet laten crashen. Het document is niet plaatsbaar → deterministisch Overig.
    docs = [
        _doc(0, _A, "subsidie cultuur"),
        _doc(1, _A, "subsidie cultuur"),
        _doc(2, _B, "vergunning bouw"),
        _doc(3, _B, "vergunning bouw"),
        _doc(8, [0.0, 0.0, 0.0], ""),
    ]
    zero_doc = docs[-1]
    params = {"onderwerp_distance": 0.5, "deelonderwerp_distance": 0.2, "min_cluster_size": 2,
              "max_chunks_per_doc": 64}
    menu = cluster_topics(docs, _bundle(no_llm=True), audit, **params)  # mag niet crashen
    assert zero_doc.topic == OVERIG and zero_doc.subtopic == OVERIG
    overig = [o for o in menu["onderwerpen"] if o["label"] == OVERIG]
    assert overig and zero_doc.id in overig[0]["deelonderwerpen"][0]["doc_ids"]


def test_chunk_cap_preserves_majority(audit):
    # 4 chunks in A, 2 in B → meerderheid A. Met cap=3 (gelijkmatig bemonsterd: chunks 0,2,4 →
    # A,A,B) blijft A de meerderheid — de cap verschuift de toewijzing niet.
    docs = [
        _doc(0, _A, "subsidie cultuur"),
        _doc(1, _A, "subsidie cultuur"),
        _doc(2, _B, "vergunning bouw"),
        _doc(3, _B, "vergunning bouw"),
        _multichunk_doc(9, [_A, _A, _A, _A, _B, _B], "subsidie cultuur vergunning"),
    ]
    split = docs[-1]
    params = {"onderwerp_distance": 0.5, "deelonderwerp_distance": 0.2, "min_cluster_size": 2,
              "max_chunks_per_doc": 3}
    cluster_topics(docs, _bundle(no_llm=True), audit, **params)
    assert split.topic != OVERIG
    assert split.topic == docs[0].topic and split.topic != docs[2].topic
