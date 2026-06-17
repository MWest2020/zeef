"""CLI-entrypoint (`zeef`) — Typer + rich.

Bevat het `converge`-commando dat de volledige pijplijn over een lokale map draait. In dit
skelet valideert het commando de vlaggen en zet het de run-omgeving + audit-log op; de stages
zelf volgen in de implementatiefase (zie openspec change converge-mvp).
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from zeef import __version__
from zeef.audit import AuditLog
from zeef.config import CutoffMode, ProfileName

app = typer.Typer(add_completion=False, help="zeef — convergentietool voor de Woo.")
console = Console()


def _resolve_cutoff(
    top_n: int | None, threshold: float | None, target: int | None
) -> tuple[CutoffMode, float | int]:
    """Precies één cutoff-modus is toegestaan; anders een duidelijke fout."""
    chosen = [
        (CutoffMode.top_n, top_n),
        (CutoffMode.threshold, threshold),
        (CutoffMode.target, target),
    ]
    active = [(mode, val) for mode, val in chosen if val is not None]
    if len(active) != 1:
        raise typer.BadParameter(
            "Kies precies één cutoff-modus: --top-n, --threshold of --target."
        )
    return active[0]


@app.command()
def converge(
    docs: Path = typer.Argument(..., exists=True, file_okay=False, help="Map met documenten."),
    query: str = typer.Option(..., "--query", "-q", help="Verfijnde zoekvraag."),
    profile: ProfileName = typer.Option(ProfileName.sovereign, "--profile"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Sla alle generatieve stappen over."),
    top_n: int | None = typer.Option(None, "--top-n"),
    threshold: float | None = typer.Option(None, "--threshold"),
    target: int | None = typer.Option(None, "--target"),
    out: Path = typer.Option(Path("runs/latest"), "--out", help="Uitvoermap voor deze run."),
) -> None:
    """Draai de convergentie over `docs` en lever inventory/relations/audit op."""
    mode, value = _resolve_cutoff(top_n, threshold, target)
    audit = AuditLog(out / "audit.jsonl")
    audit.event(
        "cli",
        "run-start",
        inputs={
            "docs": str(docs),
            "query": query,
            "profile": profile.value,
            "no_llm": no_llm,
            "cutoff_mode": mode.value,
            "cutoff_value": value,
        },
    )
    console.print(f"[bold]zeef {__version__}[/] — profiel [cyan]{profile.value}[/]"
                  f"{' [yellow](--no-llm)[/]' if no_llm else ''}")
    console.print(f"cutoff: [green]{mode.value}={value}[/]  →  uitvoer in [blue]{out}[/]")
    # De stages (ingest → … → export) volgen in de implementatiefase.
    raise typer.Exit(code=0)


@app.command()
def version() -> None:
    """Toon de versie."""
    console.print(__version__)


if __name__ == "__main__":
    app()
