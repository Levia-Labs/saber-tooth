"""Offline one-click fix of one map folder through the real Service, without the analyser."""

import shutil
from collections import Counter
from pathlib import Path

import httpx

from saber_tooth.analyser_client import AnalyserClient
from saber_tooth.service import Service, map_id_for
from saber_tooth.store import Store


def _down(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("autofix runs without the analyser")


def _make_service(levels: Path, data: Path) -> Service:
    data.mkdir(parents=True, exist_ok=True)
    client = AnalyserClient("http://analyser.invalid", data / "up", httpx.MockTransport(_down))
    return Service(levels, data, Store(data / "autofix.db"), client, shutil.copyfile)


def run_autofix(map_folder: Path, levels: Path, data: Path, max_rounds: int = 6) -> dict:
    """Copy map_folder into levels, run Service.fix_map on it and return its report."""
    map_folder, levels = Path(map_folder), Path(levels)
    levels.mkdir(parents=True, exist_ok=True)
    dest = levels / map_folder.name
    if not dest.exists():
        shutil.copytree(map_folder, dest)
    svc = _make_service(levels, Path(data))
    svc.refresh_library()
    report = svc.fix_map(map_id_for(dest.name), max_rounds)
    report["source"] = map_folder.name
    return report


def _totals(side: dict) -> dict[str, tuple[int, int]]:
    return {d: (sum(v["errors"].values()), sum(v["warnings"].values())) for d, v in side.items()}


def format_report(report: dict) -> list[str]:
    lines = [f"source {report['source']}"]
    lines.append(
        f"rounds={report['rounds']} applied={report['applied']} written={report['folder']}"
    )
    lines.append(f"difficulties={','.join(report['difficulties'])}")
    before, after = _totals(report["before"]), _totals(report["after"])
    for d in sorted(set(before) | set(after)):
        b, a = before.get(d, (0, 0)), after.get(d, (0, 0))
        lines.append(f"  {d} errors {b[0]}->{a[0]} warnings {b[1]}->{a[1]}")
        rest = report["after"].get(d, {"errors": {}, "warnings": {}})
        left = {**rest["errors"], **{f"w:{k}": c for k, c in rest["warnings"].items()}}
        if left:
            lines.append("    left " + ",".join(f"{k}={c}" for k, c in sorted(left.items())))
    why = Counter(f"{u['rule']}:{u['reason'][:40]}" for u in report["unfixed"])
    lines.append(f"unfixed={len(report['unfixed'])}")
    lines.extend(f"  no-fix {k} x{c}" for k, c in why.most_common(4))
    return lines
