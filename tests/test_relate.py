"""Relate-stage (relate-spec): 5-mail thread → één cluster; duplicaten → één telslot."""

from zeef.drivers.local import HashingEmbed
from zeef.pipeline.ingest import ingest
from zeef.pipeline.relate import relate


def _run(corpus, audit):
    docs = ingest(corpus, audit)
    relate(docs, HashingEmbed(), audit)
    return {d.source_path.split("/")[-1]: d for d in docs}, docs


def test_five_mail_thread_forms_one_cluster(corpus, audit):
    by_name, docs = _run(corpus, audit)
    thread = [by_name[f"thread-0{i}.eml"] for i in range(1, 6)]
    # Eén gedeeld thread_id over alle vijf.
    ids = {d.metadata["thread_id"] for d in thread}
    assert len(ids) == 1
    assert all(d.metadata["thread_size"] == 5 for d in thread)
    # Replies dragen een thread-parent-relatie.
    assert any(r.kind == "thread-parent" for r in by_name["thread-05.eml"].relations)
    # Precies één tip (de representant) in het cluster.
    tips = [d for d in thread if d.metadata["thread_tip"]]
    assert len(tips) == 1
    assert tips[0] is by_name["thread-05.eml"]


def test_header_threads_are_not_heuristic(corpus, audit):
    by_name, _ = _run(corpus, audit)
    rels = [r for r in by_name["thread-02.eml"].relations if r.kind == "thread-parent"]
    assert rels and "In-Reply-To" in rels[0].evidence
    assert "heuristisch" not in rels[0].evidence


def test_exact_duplicates_linked_and_counted_once(corpus, audit):
    by_name, docs = _run(corpus, audit)
    a, b = by_name["dup-a.eml"], by_name["dup-b.eml"]
    # dup-a is de representant (laagste bronpad); dup-b wijst ernaar.
    dup_rels = [r for r in b.relations if r.kind == "duplicate-of"]
    assert dup_rels and dup_rels[0].target_id == a.id
    assert "sha256" in dup_rels[0].evidence
    # De representant draagt zélf geen duplicate-of (telt als het ene slot).
    assert not any(r.kind == "duplicate-of" for r in a.relations)


def test_near_duplicate_confirmed_by_cosine(corpus, audit):
    by_name, _ = _run(corpus, audit)
    na, nb = by_name["near-a.eml"], by_name["near-b.eml"]
    linked = [d for d in (na, nb) if any(r.kind == "duplicate-of" for r in d.relations)]
    assert len(linked) == 1
    rel = next(r for r in linked[0].relations if r.kind == "duplicate-of")
    assert "cosine=" in rel.evidence


def test_heuristic_fallback_marks_evidence(audit, tmp_path):
    # Twee mails zonder threading-headers, zelfde onderwerp → heuristische thread-link.
    from email.message import EmailMessage
    from pathlib import Path

    def write(name, date):
        msg = EmailMessage()
        msg["From"] = "x@test"
        msg["Subject"] = "Re: zelfde onderwerp"
        msg["Date"] = date
        msg.set_content("Inhoud over de begroting.")
        p = Path(tmp_path) / name
        p.write_bytes(msg.as_bytes())

    write("h1.eml", "Mon, 02 Feb 2026 09:00:00 +0100")
    write("h2.eml", "Mon, 02 Feb 2026 10:00:00 +0100")
    docs = ingest(tmp_path, audit)
    relate(docs, HashingEmbed(), audit)
    rels = [r for d in docs for r in d.relations if r.kind == "thread-parent"]
    assert rels and all("heuristisch" in r.evidence for r in rels)
