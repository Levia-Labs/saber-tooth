import importlib.util
import sys
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from tests.crop_helpers import write_original

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fix_rate.py"
spec = importlib.util.spec_from_file_location("fix_rate", SCRIPT)
fr = importlib.util.module_from_spec(spec)
sys.modules["fix_rate"] = fr
spec.loader.exec_module(fr)


def side(**rules: tuple[int, int]) -> dict:
    return {
        "Easy": {
            "errors": {r: e for r, (e, _) in rules.items() if e},
            "warnings": {r: w for r, (_, w) in rules.items() if w},
        }
    }


@given(st.lists(st.integers(0, 50), max_size=30), st.integers(0, 40), st.integers(0, 5))
def test_sample_is_a_reproducible_sorted_subset(ids, n, seed):
    folders = [Path(f"m{i}") for i in set(ids)]
    got = fr.pick_sample(folders, n, seed)
    assert got == fr.pick_sample(list(reversed(folders)), n, seed)
    assert got == sorted(got) and set(got) <= set(folders)
    assert len(got) == min(n, len(folders))


def test_aggregate_sums_errors_and_warnings_per_rule():
    reports = [
        ("a", {"before": side(x=(2, 1), y=(0, 4)), "after": side(x=(0, 1))}),
        ("b", {"before": side(x=(1, 0)), "after": side()}),
    ]
    rows = fr.aggregate(reports)
    assert rows["x"] == {
        "before": 4, "after": 1, "maps_before": 2, "maps_after": 1, "failing": ["a"],
    }  # fmt: skip
    assert rows["y"]["before"] == 4 and rows["y"]["after"] == 0
    assert set(fr.aggregate(reports, "y")) == {"y"}


def test_table_has_fixed_percent_and_parse_errors():
    rows = {"x": {"before": 4, "after": 1, "maps_before": 2, "maps_after": 1}}
    lines = fr.format_table(rows, 2, ["bad boom"])
    assert lines[0] == "maps=2 parse_errors=1"
    assert "x 4 1 75.0 2 1" in lines
    assert lines[-1] == "parse-error bad boom"


def test_table_names_the_maps_each_rule_still_fails_on():
    rows = {
        "x": {"before": 4, "after": 1, "maps_before": 2, "maps_after": 1, "failing": ["a", "b"]}
    }
    assert fr.format_table(rows, 2, [])[-1] == "failing x: a; b"


def test_run_measures_copies_and_leaves_source(tmp_path, capsys):
    levels = tmp_path / "src"
    levels.mkdir()
    folder = write_original(levels)
    before = {p: p.read_bytes() for p in folder.rglob("*") if p.is_file()}
    assert fr.main([str(levels), "--sample", "1"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("maps=1 parse_errors=0")
    assert "rule before after fixed%" in out
    assert {p: p.read_bytes() for p in folder.rglob("*") if p.is_file()} == before
    assert [p.name for p in levels.iterdir()] == [folder.name]


def test_missing_dir_fails(tmp_path, capsys):
    assert fr.main([str(tmp_path / "nope")]) == 1


def test_unicode_map_names_survive_a_narrow_console(tmp_path):
    import os
    import subprocess

    (tmp_path / "日本語 (曲)").mkdir()
    env = {**os.environ, "PYTHONIOENCODING": "cp1250"}
    done = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path)],
        capture_output=True,
        env=env,
        check=False,
    )
    assert done.returncode == 0, done.stderr.decode(errors="replace")
    assert b"parse-error" in done.stdout
