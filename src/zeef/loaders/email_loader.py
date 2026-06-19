"""`.eml`/`.msg`-loader — behoudt de threading-headers (ingest-spec).

De RFC 5322-headers `Message-ID`, `In-Reply-To` en `References` blijven in de metadata, naast
afzender, ontvangers, onderwerp en datum. Bijlagen worden eigen `Document`s met een
`attachment-of`-relatie naar de e-mail. `.eml` gaat via de standaardbibliotheek; `.msg`
(Outlook-binair) wordt alleen ondersteund als `extract_msg` aanwezig is, anders een nette fout
die ingest als load-fout afvangt.
"""

from __future__ import annotations

from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from pathlib import Path

from zeef.ids import content_id
from zeef.models import Document
from zeef.normalize import normalize_text

_THREAD_HEADERS = ("Message-ID", "In-Reply-To", "References")
_ADDR_HEADERS = ("From", "To", "Cc", "Subject", "Date")


class EmailLoader:
    """Laadt een e-mail naar een body-`Document` plus één `Document` per bijlage."""

    def can_load(self, path: Path) -> bool:
        return path.suffix.lower() in (".eml", ".msg")

    def load(self, path: Path) -> list[Document]:
        if path.suffix.lower() == ".msg":
            return self._load_msg(path)
        msg = BytesParser(policy=policy.default).parse(path.open("rb"))
        return self._documents_from_message(msg, path)

    def _documents_from_message(self, msg: EmailMessage, path: Path) -> list[Document]:
        metadata = _extract_headers(msg)
        body = _extract_body(msg)
        text = normalize_text(body)
        email_doc = Document(
            id=content_id(text, str(path)),
            source_path=str(path),
            doc_type="email",
            metadata=metadata,
            text=text,
        )
        docs = [email_doc]
        for part in _attachments(msg):
            att = _attachment_document(part, path, email_doc.id)
            att.add_relation("attachment-of", email_doc.id, evidence=att.metadata["filename"])
            docs.append(att)
        return docs

    def _load_msg(self, path: Path) -> list[Document]:
        try:
            import extract_msg  # type: ignore
        except ImportError as exc:  # pragma: no cover - geen .msg-fixtures in deze change
            raise RuntimeError(
                f".msg vereist 'extract_msg' (niet geïnstalleerd): {path.name}"
            ) from exc
        m = extract_msg.Message(str(path))  # pragma: no cover
        text = normalize_text(m.body or "")  # pragma: no cover
        metadata = {  # pragma: no cover
            "Message-ID": m.messageId or "",
            "From": m.sender or "",
            "Subject": m.subject or "",
            "Date": m.date or "",
        }
        return [Document(  # pragma: no cover
            id=content_id(text, str(path)), source_path=str(path),
            doc_type="email", metadata=metadata, text=text,
        )]


def _extract_headers(msg: EmailMessage) -> dict:
    meta: dict[str, str] = {}
    for name in _THREAD_HEADERS + _ADDR_HEADERS:
        value = msg.get(name)
        if value is not None:
            meta[name] = str(value).strip()
    return meta


def _extract_body(msg: EmailMessage) -> str:
    body = msg.get_body(preferencelist=("plain", "html"))
    if body is None:
        return ""
    content = body.get_content()
    return content if isinstance(content, str) else ""


def _attachments(msg: EmailMessage) -> list[EmailMessage]:
    return [p for p in msg.iter_attachments() if p.get_filename()]


def _attachment_document(part: EmailMessage, path: Path, parent_id: str) -> Document:
    filename = part.get_filename() or "bijlage"
    maintype = part.get_content_maintype()
    text = ""
    if maintype == "text":
        payload = part.get_content()
        text = normalize_text(payload) if isinstance(payload, str) else ""
    att_path = f"{path}#att:{filename}"
    return Document(
        id=content_id(text or filename, att_path),
        source_path=att_path,
        doc_type=_doc_type_for(filename),
        metadata={"filename": filename, "content_type": part.get_content_type(),
                  "attachment_of": parent_id},
        text=text,
    )


def _doc_type_for(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return "pdf_digital"
    if ext in (".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt"):
        return "office"
    return "other"
