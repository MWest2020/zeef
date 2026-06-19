"""CLI (cli-spec): conflicterende cutoff-vlaggen afgewezen; volledige run via Typer."""

from typer.testing import CliRunner

from zeef.cli import app

runner = CliRunner()


def test_conflicting_cutoff_flags_rejected(corpus):
    result = runner.invoke(app, [
        "converge", str(corpus), "--query", "x", "--profile", "sovereign", "--no-llm",
        "--top-n", "10", "--target", "100",
    ])
    assert result.exit_code != 0
    assert "precies één" in result.output.lower() or "mutually" in result.output.lower()


def test_bare_command_defaults_to_target(corpus, tmp_path):
    # De letterlijke DoD-acceptatie-aanroep zonder cutoff-vlag → default --target 100.
    out = tmp_path / "run"
    result = runner.invoke(app, [
        "converge", str(corpus), "--query", "begroting subsidie cultuur 2026",
        "--profile", "sovereign", "--no-llm", "--out", str(out),
    ])
    assert result.exit_code == 0, result.output
    assert "default target=100" in result.output
    assert (out / "inventory.xlsx").exists()


def test_full_cli_run_produces_artifacts(corpus, tmp_path):
    out = tmp_path / "run"
    result = runner.invoke(app, [
        "converge", str(corpus), "--query", "begroting subsidie cultuur 2026",
        "--profile", "sovereign", "--no-llm", "--target", "100", "--out", str(out),
    ])
    assert result.exit_code == 0, result.output
    assert (out / "inventory.xlsx").exists()
    assert (out / "relations.json").exists()
    assert (out / "audit.jsonl").exists()
    assert "samenvatting" in result.output.lower()
