"""Mail-thread-reconstructie (relate-spec, design.md D5).

Threads worden deterministisch uit RFC 5322-headers gebouwd (`In-Reply-To` → `References`).
Ontbreken die headers, dan valt het terug op een heuristiek op onderwerp, die expliciet als
heuristisch in de `evidence` wordt gemarkeerd. Daarna worden clusters bepaald en krijgt elk
e-maildocument `thread_id`, `thread_size` en `thread_tip` in zijn metadata; de 'tip' (diepste
blad: bevat de hele draad) is de representant die als één eenheid de selectie in gaat.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from zeef.audit import AuditLog
from zeef.models import Document

STAGE = "relate"
_PREFIX = re.compile(r"^(re|fw|fwd|antw|aw)\s*:\s*", re.IGNORECASE)


def _emails(docs: list[Document]) -> list[Document]:
    return [d for d in docs if d.doc_type == "email"]


def _norm_subject(subject: str) -> str:
    prev = None
    while prev != subject:
        prev = subject
        subject = _PREFIX.sub("", subject).strip()
    return subject.lower()


def _date(doc: Document) -> datetime:
    """Altijd tz-aware (naïeve datum → UTC), zodat sorteren nooit aware/naïef mengt.

    Echte e-mail bevat zowel tijdzone-bewuste als -loze Date-headers; ze samen sorteren wierp
    voorheen `TypeError: can't compare offset-naive and offset-aware datetimes`.
    """
    try:
        dt = parsedate_to_datetime(doc.metadata.get("Date", ""))
    except (TypeError, ValueError):
        dt = None
    if dt is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def reconstruct_threads(docs: list[Document], audit: AuditLog) -> None:
    """Leg `thread-parent`-relaties: eerst op headers, anders heuristisch op onderwerp."""
    emails = _emails(docs)
    by_msgid = {d.metadata["Message-ID"]: d for d in emails if d.metadata.get("Message-ID")}
    without_headers: list[Document] = []
    for doc in emails:
        parent_id = _header_parent(doc, by_msgid)
        if parent_id is None:
            without_headers.append(doc)
            continue
        evidence = parent_id[1]
        doc.add_relation("thread-parent", by_msgid[parent_id[0]].id, evidence=evidence)
        audit.event(STAGE, "thread-link", document_ids=[doc.id, by_msgid[parent_id[0]].id],
                    inputs={"basis": "header"})
    _heuristic_threads(without_headers, audit)


def _header_parent(doc: Document, by_msgid: dict[str, Document]) -> tuple[str, str] | None:
    irt = doc.metadata.get("In-Reply-To", "").strip()
    if irt and irt in by_msgid and irt != doc.metadata.get("Message-ID"):
        return irt, f"In-Reply-To: {irt}"
    refs = doc.metadata.get("References", "").split()
    for ref in reversed(refs):
        if ref in by_msgid and ref != doc.metadata.get("Message-ID"):
            return ref, f"References: {ref}"
    return None


def _heuristic_threads(emails: list[Document], audit: AuditLog) -> None:
    by_subject: dict[str, list[Document]] = {}
    for doc in emails:
        subj = _norm_subject(doc.metadata.get("Subject", ""))
        if subj:
            by_subject.setdefault(subj, []).append(doc)
    for subj, group in by_subject.items():
        if len(group) < 2:
            continue
        ordered = sorted(group, key=_date)
        for child, parent in zip(ordered[1:], ordered):
            child.add_relation("thread-parent", parent.id,
                               evidence=f"heuristisch: gelijk onderwerp '{subj}'")
            audit.event(STAGE, "thread-link", document_ids=[child.id, parent.id],
                        inputs={"basis": "heuristiek"})


def annotate_thread_clusters(docs: list[Document]) -> None:
    """Bepaal clusters over thread-parent-edges en markeer per cluster de representant (tip)."""
    emails = _emails(docs)
    by_id = {d.id: d for d in emails}
    parent_of = {d.id: _parent_in(d, by_id) for d in emails}
    roots = {d.id: _root(d.id, parent_of) for d in emails}
    clusters: dict[str, list[Document]] = {}
    for doc in emails:
        clusters.setdefault(roots[doc.id], []).append(doc)
    children = {pid for pid in parent_of.values() if pid}
    for root, members in clusters.items():
        tip = _pick_tip(members, parent_of, children)
        for doc in members:
            doc.metadata["thread_id"] = root
            doc.metadata["thread_size"] = len(members)
            doc.metadata["thread_tip"] = doc.id == tip.id
            doc.metadata["thread_tip_id"] = tip.id


def _parent_in(doc: Document, by_id: dict[str, Document]) -> str | None:
    for rel in doc.relations:
        if rel.kind == "thread-parent" and rel.target_id in by_id:
            return rel.target_id
    return None


def _root(doc_id: str, parent_of: dict[str, str | None]) -> str:
    seen: set[str] = set()
    while parent_of.get(doc_id) and doc_id not in seen:
        seen.add(doc_id)
        doc_id = parent_of[doc_id]
    return doc_id


def _depth(doc_id: str, parent_of: dict[str, str | None]) -> int:
    depth, seen = 0, set()
    while parent_of.get(doc_id) and doc_id not in seen:
        seen.add(doc_id)
        doc_id = parent_of[doc_id]
        depth += 1
    return depth


def _pick_tip(members, parent_of, children):
    leaves = [d for d in members if d.id not in children] or members
    return max(leaves, key=lambda d: (_depth(d.id, parent_of), _date(d), d.id))
