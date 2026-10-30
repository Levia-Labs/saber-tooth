"""Resource probe: cgroup limits beat host numbers; the recommended worker cap is bounded."""

from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from saber_tooth import resources
from saber_tooth.resources import FIX_JOB_PEAK_BYTES, MEBI, recommended_max, snapshot


def put(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def host(
    monkeypatch, cores: int = 16, total: int = 32 * 1024 * MEBI, avail: int = 20 * 1024 * MEBI
):
    monkeypatch.setattr(resources, "host_cores", lambda: cores)
    monkeypatch.setattr(resources, "host_memory", lambda: (total, avail))


def test_without_cgroup_files_the_host_numbers_are_reported(tmp_path, monkeypatch):
    host(monkeypatch)
    got = snapshot(tmp_path)
    assert got["cores"] == 16
    assert got["memory"] == {
        "total": 32 * 1024 * MEBI,
        "available": 20 * 1024 * MEBI,
        "source": "host",
    }


def test_cgroup_v2_limits_win_over_the_host(tmp_path, monkeypatch):
    host(monkeypatch)
    put(tmp_path, "cpu.max", "200000 100000\n")
    put(tmp_path, "memory.max", f"{2048 * MEBI}\n")
    put(tmp_path, "memory.current", f"{512 * MEBI}\n")
    got = snapshot(tmp_path)
    assert got["cores"] == 2
    assert got["memory"] == {
        "total": 2048 * MEBI,
        "available": 1536 * MEBI,
        "source": "cgroup",
    }


def test_cgroup_v2_unlimited_values_fall_back_to_the_host(tmp_path, monkeypatch):
    host(monkeypatch)
    put(tmp_path, "cpu.max", "max 100000\n")
    put(tmp_path, "memory.max", "max\n")
    got = snapshot(tmp_path)
    assert got["cores"] == 16
    assert got["memory"]["source"] == "host"


def test_cgroup_v1_limits_are_read(tmp_path, monkeypatch):
    host(monkeypatch)
    put(tmp_path, "cpu/cpu.cfs_quota_us", "300000\n")
    put(tmp_path, "cpu/cpu.cfs_period_us", "100000\n")
    put(tmp_path, "memory/memory.limit_in_bytes", f"{4096 * MEBI}\n")
    put(tmp_path, "memory/memory.usage_in_bytes", f"{1024 * MEBI}\n")
    got = snapshot(tmp_path)
    assert got["cores"] == 3
    assert got["memory"]["total"] == 4096 * MEBI
    assert got["memory"]["available"] == 3072 * MEBI


def test_v1_no_limit_sentinel_is_ignored(tmp_path, monkeypatch):
    host(monkeypatch)
    put(tmp_path, "memory/memory.limit_in_bytes", "9223372036854771712\n")
    put(tmp_path, "cpu/cpu.cfs_quota_us", "-1\n")
    put(tmp_path, "cpu/cpu.cfs_period_us", "100000\n")
    got = snapshot(tmp_path)
    assert got["memory"]["source"] == "host"
    assert got["cores"] == 16


def test_a_fractional_quota_rounds_down_but_never_below_one(tmp_path, monkeypatch):
    host(monkeypatch)
    put(tmp_path, "cpu.max", "50000 100000\n")
    assert snapshot(tmp_path)["cores"] == 1


def test_garbage_cgroup_files_are_ignored(tmp_path, monkeypatch):
    host(monkeypatch)
    put(tmp_path, "cpu.max", "banana\n")
    put(tmp_path, "memory.max", "-5\n")
    assert snapshot(tmp_path)["cores"] == 16


def test_recommended_max_is_the_tighter_of_cores_and_memory():
    gib = 1024 * MEBI
    assert recommended_max(8, 64 * gib) == 7  # cores - 1 binds
    assert recommended_max(32, 2 * gib) == 2 * gib // FIX_JOB_PEAK_BYTES  # memory binds
    assert recommended_max(1, 64 * gib) == 1
    assert recommended_max(4, 0) == 1
    assert recommended_max(4, None) == 3  # memory unknown: cores only


@given(st.integers(1, 256), st.one_of(st.none(), st.integers(0, 2**45)))
def test_recommended_max_is_always_between_one_and_the_cap(cores, available):
    got = recommended_max(cores, available)
    assert 1 <= got <= resources.MAX_WORKERS
    assert got <= max(1, cores - 1)


def test_snapshot_reports_the_recommendation(tmp_path, monkeypatch):
    host(monkeypatch, cores=4, total=64 * 1024 * MEBI, avail=64 * 1024 * MEBI)
    got = snapshot(tmp_path)
    assert got["recommended_max"] == 3
    assert got["fix_job_peak_mb"] == FIX_JOB_PEAK_BYTES // MEBI
