"""Built frontend checks: skipped until `task st:web:build` has written web/index.html."""

import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "src" / "saber_tooth" / "web"
INDEX = WEB / "index.html"

needs_build = pytest.mark.skipif(
    not INDEX.is_file(), reason="frontend not built; run `task st:web:build`"
)

REFS = re.compile(r"""<(?:script|link)(?=\s)[^>]*?(?:src|href)=["']([^"']+)["']""")


@needs_build
def test_index_references_are_absolute_hashed_assets():
    refs = REFS.findall(INDEX.read_text(encoding="utf-8"))
    assert refs
    for ref in refs:
        assert ref.startswith("/assets/"), ref
        assert re.search(r"-[A-Za-z0-9_-]{8}\.\w+$", ref), f"not content hashed: {ref}"
        assert (WEB / ref.lstrip("/")).is_file(), ref


@needs_build
def test_index_has_a_mount_point_and_no_external_resources():
    html = INDEX.read_text(encoding="utf-8")
    assert 'id="root"' in html
    assert not re.search(r"(src|href)=[\"']https?://", html)


@needs_build
def test_bundle_has_no_external_requests():
    for path in (WEB / "assets").glob("*.js"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"""fetch\(\s*["']https?://""", text), path.name
    for path in (WEB / "assets").glob("*.css"):
        text = path.read_text(encoding="utf-8")
        assert "@import" not in text and "url(http" not in text, path.name


@needs_build
def test_tooltip_copy_ships_in_the_bundle():
    text = "".join(p.read_text(encoding="utf-8") for p in (WEB / "assets").glob("*.js"))
    assert "Nothing is written yet." in text
    assert "The original map is never changed." in text
