"""scripts/browser_check.mjs: the route list and the failure rule, read as text; no browser runs."""

from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "browser_check.mjs"
TEXT = SCRIPT.read_text(encoding="utf-8")


def routes_block() -> str:
    start = TEXT.index("const routes = [")
    return TEXT[start : TEXT.index("const profile", start)]


def test_the_vr_routes_are_loaded():
    block = routes_block()
    assert '"/vr"' in block
    assert '"/vr/beatsaver"' in block
    assert "`/vr/maps/${mapId}`" in block


def test_the_desktop_routes_are_kept():
    block = routes_block()
    for route in ('"/"', '"/beatsaver"', '"/beatsaver/playlists"', '"/about"', "`/maps/${mapId}`"):
        assert route in block


def test_any_console_error_or_page_error_still_fails_the_check():
    assert 'm.type() === "error"' in TEXT
    assert "pageerror" in TEXT


def test_the_check_stays_read_only():
    assert '["GET", "HEAD"].includes(req.method())' in TEXT
