"""Deterministische scope-regels (scope-filter-spec, design.md D5).

Een geordende lijst regels die out-of-scope materiaal uitsluiten vóór er ook maar één
LLM-call wordt gedaan. Elke regel is een pure functie `Document -> reason | None`: bij een
match geeft ze een mensleesbare reden terug, anders None. De volgorde is betekenisvol —
specifieke, goedkoop te bewijzen uitsluitingen eerst.
"""

from __future__ import annotations

import re

from zeef.models import Document

_FORWARD_PREFIX = re.compile(r"^\s*(fw|fwd|doorst)\s*:", re.IGNORECASE)
_FORWARD_MARKER = re.compile(
    r"-----\s*Original Message|-+\s*Forwarded message|Begin forwarded message|"
    r"^\s*Van:\s.+\nAan:",
    re.IGNORECASE | re.MULTILINE,
)
_PROCESS_SENDER = re.compile(r"(no-?reply|do-?not-?reply|postmaster|mailer-daemon)", re.IGNORECASE)
_PROCESS_SUBJECT = re.compile(
    r"(automati(sch|c)|ontvangstbevestiging|out of office|afwezig|read receipt|"
    r"delivery (status|failure)|niet aanwezig)",
    re.IGNORECASE,
)


def rule_forwarded_only(doc: Document) -> str | None:
    if doc.doc_type != "email":
        return None
    subject = doc.metadata.get("Subject", "")
    if not _FORWARD_PREFIX.match(subject):
        return None
    match = _FORWARD_MARKER.search(doc.text)
    if match and len(doc.text[: match.start()].strip()) < 40:
        return "alleen doorgestuurd bericht zonder eigen inhoud (regel: forwarded-only)"
    return None


def rule_calendar_invite(doc: Document) -> str | None:
    if doc.doc_type != "email":
        return None
    ctype = doc.metadata.get("content_type", "")
    subject = doc.metadata.get("Subject", "")
    if (
        "BEGIN:VCALENDAR" in doc.text
        or "text/calendar" in ctype
        or re.match(r"^\s*(uitnodiging|invitation)\s*:", subject, re.IGNORECASE)
    ):
        return "agenda-uitnodiging (regel: calendar-invite)"
    return None


def rule_process_notification(doc: Document) -> str | None:
    if doc.doc_type != "email":
        return None
    sender = doc.metadata.get("From", "")
    subject = doc.metadata.get("Subject", "")
    if _PROCESS_SENDER.search(sender) or _PROCESS_SUBJECT.search(subject):
        return "procesnotificatie / automatisch bericht (regel: process-notification)"
    return None


def rule_thread_tail(doc: Document) -> str | None:
    if doc.doc_type != "email" or doc.metadata.get("thread_size", 1) <= 1:
        return None
    if doc.metadata.get("thread_tip", True):
        return None
    tip = doc.metadata.get("thread_tip_id", "?")
    return f"eerdere mail, vertegenwoordigd door thread-head {tip} (regel: thread-tail)"


def rule_duplicate(doc: Document) -> str | None:
    for rel in doc.relations:
        if rel.kind == "duplicate-of":
            return f"duplicaat van {rel.target_id} (regel: duplicate)"
    return None


# Geordende regelset — de volgorde bepaalt welke reden een document krijgt.
RULES = (
    ("forwarded-only", rule_forwarded_only),
    ("calendar-invite", rule_calendar_invite),
    ("process-notification", rule_process_notification),
    ("thread-tail", rule_thread_tail),
    ("duplicate", rule_duplicate),
)
