"""CLI-entrypoint (`zeef`) — Typer + rich.

Het `converge`-commando valideert de vlaggen, lost het profiel op tot providers, draait de
pijplijn over een lokale map en schrijft inventory/relations/audit naar één run-map per
aanroep. De voortgang en eindsamenvatting gaan via `rich`, gescheiden van de
machineleesbare audit-trail.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from zeef import __version__
from zeef.audit import AuditLog
from zeef.config import CutoffMode, ProfileName, Settings
from zeef.pipeline.run import run_converge
from zeef.profiles import resolve_providers

app = typer.Typer(add_completion=False, help="zeef — convergentietool voor de Woo.")
console = Console()


# Default-cutoff als er geen vlag is opgegeven: recall-gericht richting de ~100-kern.
DEFAULT_CUTOFF = (CutoffMode.target, 100)


def _resolve_cutoff(
    top_n: int | None, threshold: float | None, target: int | None
) -> tuple[CutoffMode, float | int]:
    """Hoogstens één cutoff-modus; meerdere tegelijk is een fout, geen enkele → default."""
    chosen = [
        (CutoffMode.top_n, top_n),
        (CutoffMode.threshold, threshold),
        (CutoffMode.target, target),
    ]
    active = [(mode, val) for mode, val in chosen if val is not None]
    if len(active) > 1:
        raise typer.BadParameter(
            "Kies precies één cutoff-modus: --top-n, --threshold of --target."
        )
    return active[0] if active else DEFAULT_CUTOFF


def _default_out() -> Path:
    return Path("runs") / f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


@app.command()
def converge(
    docs: Path = typer.Argument(..., exists=True, file_okay=False, help="Map met documenten."),
    query: str = typer.Option(..., "--query", "-q", help="Verfijnde zoekvraag."),
    profile: ProfileName = typer.Option(ProfileName.sovereign, "--profile"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Sla alle generatieve stappen over."),
    top_n: int | None = typer.Option(None, "--top-n"),
    threshold: float | None = typer.Option(None, "--threshold"),
    target: int | None = typer.Option(None, "--target"),
    recall_bias: float = typer.Option(0.0, "--recall-bias", help="Verschuif grensgevallen richting insluiten."),
    score_top_k: int | None = typer.Option(None, "--score-top-k", help="Aantal reranked kandidaten dat de LLM scoort (0 = alle)."),
    near_dup: float | None = typer.Option(None, "--near-dup", help="Cosinus-drempel voor near-duplicates (lager = agressiever samenvouwen)."),
    out: Path | None = typer.Option(None, "--out", help="Uitvoermap voor deze run."),
) -> None:
    """Draai de convergentie over `docs` en lever inventory/relations/criteria/audit op."""
    mode, value = _resolve_cutoff(top_n, threshold, target)
    cutoff_defaulted = (top_n, threshold, target) == (None, None, None)
    out_dir = out if out is not None else _default_out()
    settings = Settings()
    top_k = settings.llm_score_top_k if score_top_k is None else score_top_k
    near_dup_threshold = settings.near_dup_threshold if near_dup is None else near_dup
    providers = resolve_providers(profile, no_llm, settings)
    audit = AuditLog(out_dir / "audit.jsonl")
    audit.event("cli", "run-start", inputs={
        "docs": str(docs), "query": query, "profile": profile.value, "no_llm": no_llm,
        "cutoff_mode": mode.value, "cutoff_value": value, "recall_bias": recall_bias,
        "score_top_k": top_k, "near_dup_threshold": near_dup_threshold,
        "cutoff_defaulted": cutoff_defaulted,
    })
    console.print(f"[bold]zeef {__version__}[/] — profiel [cyan]{profile.value}[/]"
                  f"{' [yellow](--no-llm)[/]' if no_llm else ''}")
    if cutoff_defaulted:
        console.print(f"[dim]geen cutoff opgegeven → default {mode.value}={value}[/]")
    result = run_converge(docs, query, providers, mode, value, out_dir, audit,
                          recall_bias=recall_bias, score_top_k=top_k,
                          near_dup_threshold=near_dup_threshold,
                          progress=lambda s: console.print(f"  [dim]→[/] {s}"))
    _summary(result, mode, value)


def _summary(result, mode: CutoffMode, value) -> None:
    counts = result.counts()
    table = Table(title="zeef — samenvatting", show_header=True, header_style="bold")
    for col in ("documenten", "geselecteerd", "out_of_scope", "undecided"):
        table.add_column(col, justify="right")
    table.add_row(str(counts["total"]), str(counts["selected"]),
                  str(counts["out_of_scope"]), str(counts["undecided"]))
    console.print(table)
    crit = result.criteria
    console.print(f"criteria ([cyan]{crit.source}[/]): {len(crit.items)} — "
                  + ", ".join(c.label for c in crit.items[:6]))
    console.print(f"cutoff: [green]{mode.value}={value}[/]")
    if result.manifest is not None:
        total_ms = result.manifest["runtime_ms"]["total"]
        console.print(f"runtime: [magenta]{total_ms / 1000:.1f}s[/] totaal "
                      "(per-stage in run-manifest.json)")
    console.print(f"uitvoer in [blue]{result.out_dir}[/]: "
                  "inventory.xlsx, relations.json, criteria.json, run-manifest.json, audit.jsonl")


@app.command()
def version() -> None:
    """Toon de versie."""
    console.print(__version__)


if __name__ == "__main__":
    app()
