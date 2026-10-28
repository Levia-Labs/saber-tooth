import importlib.util
import subprocess
import sys
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from tests.crop_helpers import write_original

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "profile_fix.py"
spec = importlib.util.spec_from_file_location("profile_fix", SCRIPT)
pf = importlib.util.module_from_spec(spec)
sys.modules["profile_fix"] = pf
spec.loader.exec_module(pf)


def snapshot(folder: Path) -> dict[str, bytes]:
    return {str(p.relative_to(folder)): p.read_bytes() for p in folder.rglob("*") if p.is_file()}


def test_profile_prints_phases_and_tables_without_touching_source(tmp_path, capsys):
    levels = tmp_path / "src"
    levels.mkdir()
    folder = write_original(levels)
    before = snapshot(folder)
    assert pf.main([str(folder), "--top", "5", "--rounds", "2"]) == 0
    out = capsys.readouterr().out
    for phase in ("load", "analyse", "initial checks", "fix rounds", "final checks"):
        assert f"phase {phase}:" in out or phase == "final checks"
    assert "round 1: findings=" in out
    assert "top by cumtime" in out and "top by tottime" in out
    assert "pstats: " in out
    pstats_path = Path(out.split("pstats: ")[1].split()[0])
    assert pstats_path.is_file()
    assert snapshot(folder) == before
    assert sorted(p.name for p in levels.iterdir()) == [folder.name]


def test_not_a_directory_fails(tmp_path, capsys):
    assert pf.main([str(tmp_path / "missing")]) == 1
    assert "not a directory" in capsys.readouterr().err


def test_usage_error_exits_2():
    r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    assert r.returncode == 2


def test_top_rows_and_table():
    stats = {
        ("a/b.py", 3, "f"): (1, 4, 0.5, 2.0, {}),
        ("c.py", 9, "g"): (1, 1, 1.5, 1.6, {}),
    }
    assert pf.top_rows(stats, "cumtime", 1) == [("b.py:3 f", 4, 2.0)]
    assert pf.top_rows(stats, "tottime", 2)[0] == ("c.py:9 g", 1, 1.5)
    assert pf.table("cumtime", [("x", 1, 0.5)])[1].endswith("x")


def test_round_lines():
    r = {"findings": 3, "tried": 3, "applied": 2, "check_s": 0.1, "propose_s": 0.2, "apply_s": 0.0}
    assert pf.round_lines([r]) == [
        "round 1: findings=3 tried=3 applied=2 checks=0.100s propose=0.200s apply=0.000s"
    ]


@given(st.lists(st.tuples(st.floats(0, 100), st.floats(0, 100)), max_size=20), st.integers(0, 30))
def test_top_rows_sorted_and_capped(times, n):
    stats = {("f.py", i, "fn"): (1, 1, tt, ct, {}) for i, (tt, ct) in enumerate(times)}
    rows = pf.top_rows(stats, "cumtime", n)
    assert len(rows) == min(n, len(times))
    secs = [r[2] for r in rows]
    assert secs == sorted(secs, reverse=True)
