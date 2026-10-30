"""CPU and memory the service may use: container cgroup limits first, host numbers otherwise.

`recommended_max` is the most concurrent fix or scan jobs worth running:
min(cores - 1, available memory // FIX_JOB_PEAK_BYTES), at least 1 and at most MAX_WORKERS.
One core stays free for the API and the browser; every job needs its own interpreter.
"""

import os
import sys
from pathlib import Path

MEBI = 1024 * 1024
# Peak resident size of one worker process fixing a map. Measured at about 310 MiB on the
# fixture maps (interpreter, numpy and a decoded analysis); 512 MiB leaves room for long songs.
FIX_JOB_PEAK_BYTES = 512 * MEBI
MAX_WORKERS = 16
CGROUP = Path("/sys/fs/cgroup")
_NO_LIMIT = 1 << 60  # cgroup v1 reports "unlimited" as a value near 2**63


def _number(path: Path) -> int | None:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return int(text) if text.isdigit() else None


def _cgroup_cores(root: Path) -> int | None:
    try:
        quota, period = (root / "cpu.max").read_text(encoding="utf-8").split()[:2]
        if quota.isdigit() and period.isdigit() and int(period) > 0:
            return max(1, int(quota) // int(period))
    except (OSError, ValueError):
        pass
    quota, period = _number(root / "cpu/cpu.cfs_quota_us"), _number(root / "cpu/cpu.cfs_period_us")
    if quota and period:  # v1 writes -1 for "no limit", which _number rejects
        return max(1, quota // period)
    return None


def _cgroup_memory(root: Path) -> tuple[int, int] | None:
    """(limit, used) from cgroup v2 or v1, None when no limit is set."""
    for limit_file, used_file in (
        ("memory.max", "memory.current"),
        ("memory/memory.limit_in_bytes", "memory/memory.usage_in_bytes"),
    ):
        limit = _number(root / limit_file)
        if limit is not None and limit < _NO_LIMIT:
            return limit, _number(root / used_file) or 0
    return None


def host_cores() -> int:
    counter = getattr(os, "process_cpu_count", os.cpu_count)
    return counter() or 1


def host_memory() -> tuple[int | None, int | None]:
    """(total, available) bytes of the host, None where the platform does not say."""
    if sys.platform == "win32":
        return _windows_memory()
    try:
        info = {}
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, _, rest = line.partition(":")
            info[key] = int(rest.split()[0]) * 1024
        return info.get("MemTotal"), info.get("MemAvailable")
    except (OSError, ValueError, IndexError):
        return None, None


def _windows_memory() -> tuple[int | None, int | None]:
    import ctypes

    class Status(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong)
            for name in ("total", "avail", "ptotal", "pavail", "vtotal", "vavail", "ext")
        ]

    status = Status()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None, None
    return status.total, status.avail


def recommended_max(cores: int, available: int | None) -> int:
    by_cores = max(1, cores - 1)
    by_memory = by_cores if available is None else max(1, available // FIX_JOB_PEAK_BYTES)
    return max(1, min(by_cores, by_memory, MAX_WORKERS))


def snapshot(root: Path = CGROUP) -> dict:
    """Cores, memory and the recommended worker cap, as the container sees them."""
    cores = host_cores()
    quota = _cgroup_cores(root)
    if quota is not None:
        cores = min(cores, quota)
    total, available = host_memory()
    source = "host"
    if (limit := _cgroup_memory(root)) is not None:
        total, available, source = limit[0], max(0, limit[0] - limit[1]), "cgroup"
    return {
        "cores": cores,
        "memory": {"total": total, "available": available, "source": source},
        "recommended_max": recommended_max(cores, available),
        "fix_job_peak_mb": FIX_JOB_PEAK_BYTES // MEBI,
    }
