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
    """Sluit niet-tip-berichten uit; de thread-tip vertegenwoordigt het thread.

    BEKEND RECALL-RISICO (latent, niet-actief — geen fix nu).
    De aanname is dat de tip (diepste/laatste reply, zie threads._pick_tip) de inhoud van het thread
    draagt. Dat klopt voor echte e-mail waar de laatste reply de gequote historie meeneemt: de
    validity-gate telt `len(doc.text)` inclusief quotes, dus zo'n tip overleeft. Het bezwijkt alleen
    in de smalle conditie *RFC 5322-gethreade mail ÉN een quote-vrije/korte tip*: dan collapst deze
    regel het inhoudelijke eerdere bericht naar een tip die de validity-gate vervolgens als
    `empty-after-ocr` laat vallen → het hele thread (incl. enig relevant bericht) verdwijnt
    pre-retrieve. Waargenomen op een synthetisch e-mailcorpus (kunstmatig lege tips); een
    recall-cap van 0.61 daar.
    Kán NIET spelen op PDF-dossiers: die missen e-mailheaders, dus deze regel vuurt nooit
    (bevestigd: 0 vuringen op het Woo-PDF-corpus). Wordt een Woo-verzoek ooit een écht gethread
    e-mailcorpus, dan is de recall-safe variant (collapse alleen als de tip de validity-gate
    overleeft, anders het inhoudrijkste overlevende bericht behouden) een aparte OpenSpec-change.
    """
    if doc.doc_type != "email" or doc.metadata.get("thread_size", 1) <= 1:
        return None
    if doc.metadata.get("thread_tip", True):
        return None
    tip = doc.metadata.get("thread_tip_id", "?")
    return f"eerdere mail, vertegenwoordigd door thread-head {tip} (regel: thread-tail)"


# Let op: er is bewust GÉÉN `rule_duplicate` meer. Inhoud-duplicaten (`duplicate-of`, gelegd door
# `relate`) mogen niet vóór de ranking worden uitgesloten — dat zou een verborgen recall-gate zijn
# (converge-ranking invariant D20.5). De collapse van een duplicaatgroep gebeurt in `select`, ná de
# cosine-ranking, met de hoogst gerangschikte als representant (D16). De thread-tail-regel hieronder
# dekt nog wél de procesrol "eerdere mail, al vertegenwoordigd door de thread-head".


# Geordende regelset — de volgorde bepaalt welke reden een document krijgt.
RULES = (
    ("forwarded-only", rule_forwarded_only),
    ("calendar-invite", rule_calendar_invite),
    ("process-notification", rule_process_notification),
    ("thread-tail", rule_thread_tail),
)
