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


def test_files_exist():
    for name in FILES:
        assert (WEB / name).is_file(), name


def test_js_files_within_line_limit():
    for path in WEB.glob("*.js"):
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 300, path.name


REQUEST = r"""request\(\s*["'](GET|POST)["']\s*,\s*[`'"](/api/[^`'"\s]*)[`'"]"""


def _js_sources():
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(WEB.glob("*.js")))


def test_js_uses_only_contract_routes():
    source = _js_sources()
    calls = re.findall(REQUEST, source)
    used = {(m, re.sub(r"\$\{[^}]*\}", "{id}", p.split("?")[0])) for m, p in calls}
    assert used == ROUTES
    literals = re.findall(r"""[`'"](/api/[^`'"\s]*)[`'"]""", source)
    assert len(literals) == len(calls)


def test_no_external_resources_or_innerhtml():
    texts = {n: (WEB / n).read_text(encoding="utf-8") for n in FILES}
    texts.update({p.name: p.read_text(encoding="utf-8") for p in WEB.glob("*.js")})
    for name, text in texts.items():
        assert not re.search(r"(src|href)=[\"']https?://", text), name
        assert not re.search(r"""(import\s*\(?|from)\s*["']https?://""", text), name
        assert "innerHTML" not in text and "outerHTML" not in text, name
        assert "insertAdjacentHTML" not in text and "document.write" not in text, name
        assert "@import" not in text, name


def test_index_links_assets():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    for asset in ("style.css", "app.js"):
        assert asset in html
    assert "aria-live" in html
