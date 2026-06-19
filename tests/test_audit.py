"""Audit-trail (design.md D7): append-only JSONL, model/location/prompt vastgelegd."""

import json

from zeef.audit import AuditLog


def _read(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_events_are_appended_as_jsonl(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    log.event("ingest", "loaded", document_ids=["a"])
    log.event("select", "selected", document_ids=["a"], inputs={"mode": "top-n", "value": 50})
    records = _read(tmp_path / "audit.jsonl")
    assert len(records) == 2
    assert records[0]["stage"] == "ingest"
    assert records[0]["document_ids"] == ["a"]
    assert records[1]["inputs"]["mode"] == "top-n"
    assert all("ts" in r for r in records)


def test_llm_event_records_model_location_and_prompt(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    log.event(
        "scope-filter",
        "llm-decision",
        document_ids=["x"],
        model="qwen3",
        location="local",
        prompt="Is dit document in scope? ...",
    )
    rec = _read(tmp_path / "audit.jsonl")[0]
    assert rec["model"] == "qwen3"
    assert rec["location"] == "local"
    assert rec["prompt"].startswith("Is dit document in scope?")


def test_log_is_append_only_across_instances(tmp_path):
    p = tmp_path / "audit.jsonl"
    AuditLog(p).event("a", "x")
    AuditLog(p).event("b", "y")
    assert len(_read(p)) == 2
