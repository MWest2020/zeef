"""Scope-filter (scope-filter-spec): regels sluiten uit zonder LLM; --no-llm laat residu staan."""

import json

from zeef.config import ProfileName, Settings
from zeef.drivers.local import HashingEmbed
from zeef.pipeline.ingest import ingest
from zeef.pipeline.relate import relate
from zeef.pipeline.scope_filter import scope_filter
from zeef.profiles import ProviderBundle, resolve_providers


def _prepared(corpus, audit):
    docs = ingest(corpus, audit)
    relate(docs, HashingEmbed(), audit)
    return docs, {d.source_path.split("/")[-1]: d for d in docs}


def _bundle(no_llm=True):
    return resolve_providers(ProfileName.sovereign, no_llm=no_llm, settings=Settings(_env_file=None))


def _events(audit):
    return [json.loads(line) for line in audit.path.read_text(encoding="utf-8").splitlines()]


def test_calendar_invite_excluded_without_llm(corpus, audit):
    docs, by_name = _prepared(corpus, audit)
    scope_filter(docs, _bundle(no_llm=True), audit, query="begroting subsidie cultuur 2026")
    invite = by_name["agenda-uitnodiging.eml"]
    assert invite.decision == "out_of_scope"
    assert "calendar-invite" in invite.decision_reason
    # Geen enkele LLM-beslissing in --no-llm.
    assert not [e for e in _events(audit) if e["action"] == "llm-decision"]


def test_process_notification_excluded(corpus, audit):
    docs, by_name = _prepared(corpus, audit)
    scope_filter(docs, _bundle(), audit, query="x")
    assert by_name["notificatie.eml"].decision == "out_of_scope"
    assert "process-notification" in by_name["notificatie.eml"].decision_reason


def test_thread_tail_excluded_tip_kept(corpus, audit):
    docs, by_name = _prepared(corpus, audit)
    scope_filter(docs, _bundle(), audit, query="x")
    tail = [by_name[f"thread-0{i}.eml"] for i in range(1, 5)]
    assert all(d.decision == "out_of_scope" and "thread-tail" in d.decision_reason for d in tail)
    assert by_name["thread-05.eml"].decision == "undecided"  # tip blijft staan


def test_duplicate_excluded_with_reason(corpus, audit):
    docs, by_name = _prepared(corpus, audit)
    scope_filter(docs, _bundle(), audit, query="x")
    assert by_name["dup-b.eml"].decision == "out_of_scope"
    assert "duplicate" in by_name["dup-b.eml"].decision_reason
    assert by_name["dup-a.eml"].decision == "undecided"


def test_every_exclusion_has_nonempty_reason(corpus, audit):
    docs, _ = _prepared(corpus, audit)
    scope_filter(docs, _bundle(), audit, query="x")
    for doc in docs:
        if doc.decision == "out_of_scope":
            assert doc.decision_reason.strip()


def test_no_llm_leaves_residue_undecided(corpus, audit):
    docs, _ = _prepared(corpus, audit)
    scope_filter(docs, _bundle(no_llm=True), audit, query="x")
    # Er is residu (bv. de digitale PDF, de thread-tip), en dat blijft undecided.
    assert any(d.decision == "undecided" for d in docs)
    skipped = [e for e in _events(audit) if e["action"] == "llm-skipped"]
    assert skipped


def test_llm_scope_is_recall_oriented():
    from zeef.pipeline.scope_filter import _is_exclude_verdict

    # Alleen een expliciet 'UITSLUITEN' sluit uit; al het andere behoudt (recall-veilig).
    assert _is_exclude_verdict("UITSLUITEN")
    assert _is_exclude_verdict("uitsluiten: ander onderwerp")
    assert not _is_exclude_verdict("BEHOUDEN")
    assert not _is_exclude_verdict("Niet uitsluiten")  # twijfel → behouden
    assert not _is_exclude_verdict("")  # leeg → behouden


def test_llm_excludes_only_on_uitsluiten(corpus, audit):
    docs = ingest(corpus, audit)
    relate(docs, HashingEmbed(), audit)

    class ExcludeAll:
        name = "fake-llm"
        location = "local"

        def complete(self, prompt, *, system=None):
            return "UITSLUITEN"

    bundle = ProviderBundle(llm=ExcludeAll(), embed=HashingEmbed(),
                            reranker=_bundle().reranker, no_llm=False)
    scope_filter(docs, bundle, audit, query="iets totaal anders")
    # Met UITSLUITEN belandt het hele residu out_of_scope met de juiste reden.
    excluded = [d for d in docs if d.decision == "out_of_scope" and "UITSLUITEN" in d.decision_reason]
    assert excluded


def test_llm_fallback_only_for_residue_and_logs_prompt(corpus, audit):
    docs, _ = _prepared(corpus, audit)

    class FakeLLM:
        name = "fake-llm"
        location = "local"

        def __init__(self):
            self.calls = []

        def complete(self, prompt, *, system=None):
            self.calls.append(prompt)
            return "RELEVANT"

    from zeef.pipeline.scope_rules import RULES

    # Tel vooraf hoeveel documenten een regel zou uitsluiten (die mogen níét naar de LLM).
    rule_excluded = sum(1 for d in docs if any(rule(d) for _, rule in RULES))
    fake = FakeLLM()
    bundle = ProviderBundle(llm=fake, embed=HashingEmbed(),
                            reranker=_bundle().reranker, no_llm=False)
    scope_filter(docs, bundle, audit, query="begroting")
    # FakeLLM zegt altijd RELEVANT, dus het residu blijft undecided; #calls == #residu.
    residue = sum(1 for d in docs if d.decision == "undecided")
    assert rule_excluded > 0
    assert len(fake.calls) == residue
    llm_events = [e for e in _events(audit) if e["action"] == "llm-decision"]
    assert llm_events and all(e["prompt"] and e["model"] == "fake-llm" for e in llm_events)
