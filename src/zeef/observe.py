"""`--observe` — leesbare per-stap terminalweergave tijdens een run (default uit).

Aangezet via `--observe` of `ZEEF_OBSERVE=1`. Voegt GEEN meet-logica toe en wijzigt de
pijplijn-logica niet: het leest uitsluitend de audit-events die elke stap zelf al schrijft
(`audit.jsonl`) en rendert per stap een rich-panel met STAP · INPUT · OUTPUT · KEUZE · HERKOMST.

De soeverein/cloud-regel wordt niet blind gehardcodeerd maar afgeleid van de provider die de
stap feitelijk gebruikte (`providers.embed/reranker/llm`, dezelfde bron als het run-manifest).
De per-stap-extractie staat in observe_blocks.py; dit bestand doet alleen IO + rendering.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from zeef.observe_blocks import build

# Werkwoord per stap voor de voortgangsregel (alleen cosmetisch).
_PROGRESS_VERB = {"ingest": "ingelezen", "retrieve": "embedded", "embed": "embedded"}

# Korte, statische stap-omschrijving (de cijfers/provider komen uit de run zelf).
_TITLES = {
    "criteria": "criteria — zoekvraag → scoringscriteria",
    "ingest": "ingest — bronbestanden inlezen",
    "validity": "validity — leesbaarheids-gate",
    "relate": "relate — duplicaten & overlap",
    "scope-filter": "scope-filter — buiten scope eruit",
    "retrieve": "retrieve — embedding-relevantie",
    "rerank": "rerank — lexicale herordening",
    "score": "score — relevantiescore",
    "select": "select — kern afsnijden",
    "topics": "topics — thematische clustering",
    "summarise": "summarise — samenvattingen",
    "export": "export — artefacten schrijven",
}


class StageObserver:
    """Rendert per stap één panel uit de net-bijgeschreven audit-events."""

    def __init__(self, audit_path: Path, providers: Any, console: Console | None = None) -> None:
        self.path = Path(audit_path)
        self.providers = providers
        self.console = console or Console()
        # Begin ná wat er nu al staat (bv. het cli run-start-event), zodat we alleen stap-events lezen.
        self._offset = self.path.stat().st_size if self.path.exists() else 0

    def _read_new(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as fh:
            fh.seek(self._offset)
            data = fh.read()
            self._offset = fh.tell()
        out: list[dict] = []
        for line in data.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return out

    def _prov(self, role: str) -> tuple[str, str]:
        prov = getattr(self.providers, role, None)
        return getattr(prov, "name", "?"), getattr(prov, "location", "?")

    def progress_for(self, stage: str) -> Callable[[int, int], None]:
        """Per-item voortgangscallback voor een lange stap (ingest/retrieve/embed).

        Begrensd tot ~20 platte regels per stap (print bij elke ~5% en altijd op het laatste
        item), zodat een omgeleide observe-log leesbaar en tail-vriendelijk blijft. Schrijft
        niets naar de audit-trail en raakt geen resultaten: puur cosmetisch.
        """
        verb = _PROGRESS_VERB.get(stage, "verwerkt")

        def _cb(done: int, total: int) -> None:
            if total <= 0:
                return
            step = max(1, total // 20)
            if done % step == 0 or done == total:
                self.console.print(f"  [dim]{stage}: {verb} {done}/{total}[/dim]")

        return _cb

    def render(self, stage: str) -> None:
        """Hook na elke stap: lees de nieuwe audit-regels en print het panel (faalt nooit hard)."""
        events = [e for e in self._read_new() if e.get("stage") == stage]
        if not events:
            return
        try:
            block = build(stage, events, self._prov)
        except Exception:  # observability mag een run nooit breken
            return
        if block is not None:
            self._panel(stage, block)

    def _panel(self, stage: str, block: dict) -> None:
        grid = Table.grid(padding=(0, 2))
        grid.add_column(justify="right", style="bold cyan", no_wrap=True)
        grid.add_column()
        grid.add_row("INPUT", block["input"])
        grid.add_row("OUTPUT", block["output"])
        keuze = block["keuze"]
        grid.add_row("KEUZE", keuze[0] if isinstance(keuze, list) else keuze)
        for extra in (keuze[1:] if isinstance(keuze, list) else []):
            grid.add_row("", f"[dim]{extra}[/dim]")
        grid.add_row("HERKOMST", block["herkomst"])
        self.console.print(Panel(grid, title=f"[bold]{_TITLES.get(stage, stage)}[/bold]",
                                 title_align="left", border_style="blue", expand=False))
