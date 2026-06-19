"""Select-stage (select-spec): drie modi reproduceerbaar; recall-bias sluit grensgeval in."""

import json

from zeef.audit import AuditLog
from zeef.config import CutoffMode
from zeef.models import Document


def _mk(scores):
    docs = []
    for i, s in enumerate(scores):
        d = Document(id=f"d{i:03d}", source_path=f"/d{i}", doc_type="other", text="t")
        d.scores["final"] = s
        docs.append(d)
    return docs


def _audit(tmp_path):
    return AuditLog(tmp_path / "a.jsonl")


def _last_select_event(audit):
    events = [json.loads(line) for line in audit.path.read_text().splitlines()]
    return [e for e in events if e["action"] == "select"][-1]


def test_top_n_selects_hard_count(tmp_path):
    from zeef.pipeline.select import select

    docs = _mk([1.0 - i * 0.001 for i in range(100)])
    selected = select(docs, CutoffMode.top_n, 50, _audit(tmp_path))
    assert len(selected) == 50
    assert all(d.decision == "selected" for d in selected)
    assert sum(1 for d in docs if d.decision == "selected") == 50


def test_threshold_selects_by_score(tmp_path):
    from zeef.pipeline.select import select

    docs = _mk([1.0 - i * 0.001 for i in range(100)])
    selected = select(docs, CutoffMode.threshold, 0.95, _audit(tmp_path))
    assert all(d.scores["final"] >= 0.95 for d in selected)
    assert all(d.scores["final"] < 0.95 for d in docs if d.decision != "selected")


def test_target_reports_knee(tmp_path):
    from zeef.pipeline.select import select

    scores = [0.9 - i * 0.001 for i in range(30)] + [0.5 - j * 0.001 for j in range(30)]
    audit = _audit(tmp_path)
    selected = select(_mk(scores), CutoffMode.target, 30, audit)
    assert len(selected) == 30
    knee = _last_select_event(audit)["inputs"]["knee"]
    assert knee["index"] == 30
    assert knee["gap"] > 0.3  # de duidelijke knik tussen het hoge en lage blok


def test_selection_is_reproducible(tmp_path):
    from zeef.pipeline.select import select

    scores = [0.5 + (i % 7) * 0.01 for i in range(40)]  # met herhaalde scores (ties)
    # Zelfde id↔score-afbeelding, andere invoervolgorde → identieke selectie (tie-break op id).
    a = {d.id for d in select(_mk(scores), CutoffMode.top_n, 15, _audit(tmp_path))}
    b = {d.id for d in select(list(reversed(_mk(scores))), CutoffMode.top_n, 15, _audit(tmp_path))}
    assert a == b


def test_recall_bias_includes_near_threshold(tmp_path):
    from zeef.pipeline.select import select

    docs = _mk([0.90, 0.85, 0.79])  # laatste net onder de drempel 0.80
    audit = _audit(tmp_path)
    select(docs, CutoffMode.threshold, 0.80, audit, recall_bias=0.02)
    assert docs[2].decision == "selected"
    assert "recall-bias" in docs[2].decision_reason
    assert _last_select_event(audit)["inputs"]["recall_bias"] == 0.02


def test_no_recall_bias_drops_near_threshold(tmp_path):
    from zeef.pipeline.select import select

    docs = _mk([0.90, 0.85, 0.79])
    select(docs, CutoffMode.threshold, 0.80, _audit(tmp_path), recall_bias=0.0)
    assert docs[2].decision != "selected"
