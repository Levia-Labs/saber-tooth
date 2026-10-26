"""Static frontend checks: files exist and app.js only uses contract routes."""

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "src" / "saber_tooth" / "web"
FILES = ("index.html", "app.js", "timeline.js", "style.css")

ROUTES = {
    ("GET", "/api/maps"),
    ("POST", "/api/maps/{id}/scan"),
    ("GET", "/api/maps/{id}/proposals"),
    ("POST", "/api/proposals/{id}/approve"),
    ("POST", "/api/proposals/{id}/reject"),
    ("POST", "/api/maps/{id}/approve-all"),
    ("POST", "/api/maps/{id}/apply"),
    ("POST", "/api/generate"),
    ("POST", "/api/lightshow/learn"),
    ("GET", "/api/jobs/{id}"),
}
PATHS = {path for _, path in ROUTES}


def test_files_exist():
    for name in FILES:
        assert (WEB / name).is_file(), name


def test_js_files_within_line_limit():
    for path in WEB.glob("*.js"):
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 300, path.name


def test_js_uses_only_contract_routes():
    source = "\n".join(p.read_text(encoding="utf-8") for p in WEB.glob("*.js"))
    literals = re.findall(r"""[`'"](/api/[^`'"\s]*)[`'"]""", source)
    assert literals
    used = set()
    for literal in literals:
        path = re.sub(r"\$\{[^}]*\}", "{id}", literal.split("?")[0])
        assert path in PATHS, literal
        used.add(path)
    assert used == PATHS


def test_no_external_resources_or_innerhtml():
    for name in FILES:
        text = (WEB / name).read_text(encoding="utf-8")
        assert not re.search(r"(src|href)=[\"']https?://", text), name
        assert "innerHTML" not in text, name
        assert "@import" not in text, name


def test_index_links_assets():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    for asset in ("style.css", "app.js"):
        assert asset in html
    assert "aria-live" in html
