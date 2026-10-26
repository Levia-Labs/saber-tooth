"""Unit tests for scripts/readme_check.py folder selection (no git calls)."""

import importlib.util
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

_SPEC = importlib.util.spec_from_file_location(
    "readme_check", Path(__file__).resolve().parents[1] / "scripts" / "readme_check.py"
)
assert _SPEC and _SPEC.loader
rc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rc)

FILES = [
    "README.md",
    "pyproject.toml",
    "src/saber_tooth/cli.py",
    "src/saber_tooth/service/core.py",
    "tests/test_x.py",
    "tests/fixtures/maps/a.json",
    "tests/fixtures/maps/m1/Info.dat",
    "tests/fixtures/maps/m1/sub/x.dat",
    "tests/fixtures/analyser/b.json",
    "tests/fixtures/analyser/leaf/y.json",
    ".crepidoma/configs/ruff.toml",
    "node_modules/x/index.js",
    "src/pkg/__pycache__/a.pyc",
    ".superpowers/s/p.md",
    ".ratchet/r.json",
    ".venv/lib/z.py",
]


def test_root_counted():
    assert "." in rc.required_folders(FILES)


def test_excludes():
    got = rc.required_folders(FILES)
    for bad in (".crepidoma", ".crepidoma/configs", "node_modules/x", ".ratchet", ".venv/lib"):
        assert bad not in got
    assert not any("__pycache__" in g or ".superpowers" in g for g in got)


def test_fixture_leaves_excluded_but_roots_kept():
    got = rc.required_folders(FILES)
    assert "tests/fixtures/maps" in got
    assert "tests/fixtures/analyser" in got
    assert "tests/fixtures/maps/m1" not in got
    assert "tests/fixtures/maps/m1/sub" not in got
    assert "tests/fixtures/analyser/leaf" not in got


def test_ancestors_included_and_sorted():
    got = rc.required_folders(FILES)
    assert "src" in got and "src/saber_tooth" in got and "src/saber_tooth/service" in got
    assert got == sorted(got)


def test_missing_uses_predicate():
    got = rc.missing_folders(["a/x", "b/y"], lambda d: d == "a")
    assert got == [".", "b"]


def test_format_caps_lines():
    out = rc.format_report([f"d{i}" for i in range(25)], cap=20)
    assert out[:20] == [f"d{i}" for i in range(20)]
    assert out[20] == "... 5 more"
    assert out[-1] == "missing=25"


def test_format_no_missing():
    assert rc.format_report([], cap=20) == ["missing=0"]


@given(st.lists(st.from_regex(r"[a-z]{1,4}(/[a-z]{1,4}){0,3}\.py", fullmatch=True), max_size=20))
def test_required_subset_of_ancestors(paths):
    got = rc.required_folders(paths)
    assert "." in got
    for g in got:
        assert g == "." or any(p.startswith(g + "/") for p in paths)
