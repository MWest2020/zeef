"""Append-only JSONL audit-trail — de differentiator (design.md D7).

Eén gestructureerd event per stage-actie. Geen ad-hoc prints. Uit deze log moeten zowel
de geselecteerde kern als de uitgesloten rest volledig reconstrueerbaar zijn, inclusief
welk model is gebruikt en wáár het draaide (lokaal/cloud), en bij LLM de exacte prompt.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLog:
    """Schrijft events regel-voor-regel naar `audit.jsonl` (append-only)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def event(
        self,
        stage: str,
        action: str,
        *,
        document_ids: list[str] | None = None,
        inputs: dict[str, Any] | None = None,
        model: str | None = None,
        location: str | None = None,
        prompt: str | None = None,
        **extra: Any,
    ) -> None:
        """Leg één stage-actie vast.

        `model`/`location` worden gevuld bij LLM-, embedding- of rerank-calls; `prompt`
        uitsluitend bij LLM-calls (de exacte verzonden prompt).
        """
        record: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "action": action,
        }
        if document_ids is not None:
            record["document_ids"] = document_ids
        if inputs is not None:
            record["inputs"] = inputs
        if model is not None:
            record["model"] = model
        if location is not None:
            record["location"] = location
        if prompt is not None:
            record["prompt"] = prompt
        record.update(extra)

        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
