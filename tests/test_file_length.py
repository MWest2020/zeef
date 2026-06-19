"""Hard limiet uit de brief (design.md D8): geen broncodebestand boven 200 regels.

Een test i.p.v. een aparte CI-tool houdt de grens lokaal en in CI groen-of-rood, zonder
extra gereedschap. Drijft de splitsing langs natuurlijke naden (één loader/driver/stage
per bestand) en houdt de review behapbaar.
"""

from pathlib import Path

MAX_LINES = 200
SRC = Path(__file__).resolve().parent.parent / "src" / "zeef"


def test_no_source_file_exceeds_200_lines():
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        n = sum(1 for _ in path.open(encoding="utf-8"))
        if n > MAX_LINES:
            offenders.append(f"{path.relative_to(SRC.parent.parent)}: {n} regels")
    assert not offenders, "Bestanden boven de 200-regellimiet:\n" + "\n".join(offenders)
