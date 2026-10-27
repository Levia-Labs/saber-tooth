"""Static frontend checks: files exist and the JS only uses contract routes."""

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "src" / "saber_tooth" / "web"
FILES = (
    "index.html",
    "app.js",
    "router.js",
    "urlstate.js",
    "library.js",
    "mappage.js",
    "newmap.js",
    "tooltip.js",
    "icons.js",
    "timeline.js",
    "style.css",
    "library.css",
    "page.css",
)

ROUTES = {
    ("GET", "/api/maps"),
    ("GET", "/api/maps/{id}"),
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


def test_cover_comes_from_the_api_url_only():
    source = _js_sources()
    assert "cover_url" in source
    assert "/cover" not in source


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
    for asset in ('href="/style.css"', 'src="/app.js"', 'href="/favicon.svg"'):
        assert asset in html
    assert "aria-live" in html


def test_index_has_sprite_for_every_icon_used():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    symbols = set(re.findall(r'<symbol id="i-([a-z-]+)"', html))
    used = set(re.findall(r'icon\(\s*"([a-z-]+)"', _js_sources()))
    used |= set(re.findall(r'^\s+name: "([a-z-]+)",$', _js_sources(), re.MULTILINE))
    used |= set(re.findall(r'href="#i-([a-z-]+)"', html))
    assert used <= symbols, used - symbols


def test_tooltip_copy_present():
    tips = (WEB / "tips.js").read_text(encoding="utf-8")
    assert "Nothing is written yet." in tips
    assert "The original map is never changed." in tips


def test_index_asset_references_are_absolute():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    refs = re.findall(r"""<(?:script|link)(?=\s)[^>]*?(?:src|href)=["']([^"']+)["']""", html)
    assert refs
    for ref in refs:
        assert ref.startswith("/"), ref
