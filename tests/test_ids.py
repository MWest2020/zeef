"""Contracttest voor de losstaande `zeef.ids` module (cross-repo `doc_id`).

`content_id` is het gedeelde contract met o.a. `zeef-eval`. De digest is bevroren: deze
test pint de exacte uitkomst van een bekende invoer, zodat een onbedoelde wijziging aan de
afleiding meteen rood wordt en niet stilletjes de cross-repo ids laat verschuiven.
"""

from zeef.ids import ID_LENGTH, content_id


def test_content_id_pins_known_digest():
    # sha256("hallo wereld" + b"\x00" + "/docs/a.eml")[:16]
    assert content_id("hallo wereld", "/docs/a.eml") == "adc2593a9b367eb3"


def test_content_id_length_matches_constant():
    assert len(content_id("x", "/y")) == ID_LENGTH


def test_content_id_is_reproducible():
    assert content_id("zelfde tekst", "/p") == content_id("zelfde tekst", "/p")


def test_content_id_differs_on_source_path():
    assert content_id("zelfde tekst", "/docs/a.eml") != content_id("zelfde tekst", "/docs/b.eml")


def test_ids_module_imports_without_pydantic():
    # Het contract: `zeef.ids` is afhankelijkheidsvrij. In een verse interpreter, na het
    # importeren van zeef.ids, mag pydantic/de pijplijn niet zijn meegeladen. Zo blijft het
    # cross-repo importeerbaar zonder de hele pijplijn.
    import subprocess
    import sys

    code = (
        "import sys; import zeef.ids; "
        "assert 'pydantic' not in sys.modules, sorted(m for m in sys.modules if 'zeef' in m); "
        "assert 'zeef.models' not in sys.modules; print('ok')"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "ok"
