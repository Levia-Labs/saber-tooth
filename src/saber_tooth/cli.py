"""saber-tooth command line: check, inspect, survey, learn, gen-url."""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

import httpx

from saber_tooth.checks import Finding, run_checks
from saber_tooth.lightshow import learn
from saber_tooth.mapio import MapParseError, load_map
from saber_tooth.timing import Timing

MAX_LINES = 20
DEFAULT_API = "http://127.0.0.1:8100"


def _emit(lines: list[str], tail: list[str]) -> None:
    """Print lines then tail, never more than MAX_LINES in total."""
    room = MAX_LINES - len(tail)
    if len(lines) > room:
        hidden = len(lines) - (room - 1)
        lines = [*lines[: room - 1], f"... {hidden} more"]
    print("\n".join([*lines, *tail]))


def _cmd_check(args: argparse.Namespace) -> int:
    try:
        findings = run_checks(load_map(Path(args.folder)))
    except (MapParseError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps([f.to_dict() for f in findings]))
        return 0
    counts: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for f in findings:
        counts[(f.rule, f.difficulty)][0 if f.severity == "error" else 1] += 1
    lines = [f"{r} {d} errors={c[0]} warnings={c[1]}" for (r, d), c in sorted(counts.items())]
    errors = sum(c[0] for c in counts.values())
    warns = sum(c[1] for c in counts.values())
    _emit(lines, [f"total errors={errors} warnings={warns}"])
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    try:
        m = load_map(Path(args.folder))
    except (MapParseError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    i = m.info
    lines = [
        f"title {i.song_name}",
        f"mapper {i.mapper}",
        f"bpm {i.bpm:g}",
        f"environment {i.environment}",
    ]
    for name, d in m.difficulties.items():
        secs = Timing(i.bpm, d.bpm_events).to_seconds(max((n.beat for n in d.notes), default=0))
        nps = len(d.notes) / secs if secs > 0 else 0.0
        lines.append(f"{name} notes={len(d.notes)} nps={nps:.2f}")
    _emit(lines, [])
    return 0


def _survey_findings(folder: Path) -> list[Finding]:
    return run_checks(load_map(folder))


def _cmd_survey(args: argparse.Namespace) -> int:
    root = Path(args.levels_dir)
    stats: dict[str, list] = defaultdict(lambda: [0, 0, 0])
    parse_errors = 0
    try:
        folders = sorted(p for p in root.iterdir() if p.is_dir())
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for folder in folders:
        try:
            findings = _survey_findings(folder)
        except Exception:  # one broken map must not abort the survey
            parse_errors += 1
            continue
        for rule in {f.rule for f in findings}:
            s = stats[rule]
            s[0] += sum(f.rule == rule and f.severity == "error" for f in findings)
            s[1] += sum(f.rule == rule and f.severity != "error" for f in findings)
            s[2] += 1
    lines = [f"{r} errors={s[0]} warnings={s[1]} maps={s[2]}" for r, s in sorted(stats.items())]
    _emit(lines, [f"parse_errors={parse_errors}"])
    return 0


def _cmd_learn(args: argparse.Namespace) -> int:
    try:
        templates = learn(Path(args.levels_dir))
        templates.save(Path(args.out))
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    lines = [f"{env} units={len(us)}" for env, us in sorted(templates.units.items())]
    total = sum(len(us) for us in templates.units.values())
    _emit(lines, [f"total units={total}"])
    return 0


def gen_url(url: str, api: str, transport: httpx.BaseTransport | None = None) -> str:
    """Post a song URL to the generate endpoint and return the job id."""
    with httpx.Client(transport=transport, timeout=30) as client:
        resp = client.post(f"{api.rstrip('/')}/api/generate", json={"url": url})
        resp.raise_for_status()
        data = resp.json()
    if not isinstance(data, dict):
        raise ValueError(f"unexpected response: {str(data)[:80]}")
    job = data.get("job") or data.get("id") or data.get("job_id")
    if job is None:
        raise ValueError(f"unexpected response: {str(data)[:80]}")
    return str(job)


def scan_api(map_id: str, api: str, transport: httpx.BaseTransport | None = None) -> str:
    """Ask the running API to scan one map and return the job id."""
    with httpx.Client(transport=transport, timeout=30) as client:
        resp = client.post(f"{api.rstrip('/')}/api/maps/{quote(map_id, safe='')}/scan")
        resp.raise_for_status()
        data = resp.json()
    if not isinstance(data, dict) or data.get("job") is None:
        raise ValueError(f"unexpected response: {str(data)[:80]}")
    return str(data["job"])


def _cmd_scan_api(args: argparse.Namespace) -> int:
    try:
        print(scan_api(args.map_id, args.api))
    except (httpx.HTTPError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _cmd_gen_url(args: argparse.Namespace) -> int:
    try:
        print(gen_url(args.url, args.api))
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="saber-tooth")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check", help="run map checks on a folder")
    c.add_argument("folder")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=_cmd_check)
    i = sub.add_parser("inspect", help="show map metadata")
    i.add_argument("folder")
    i.set_defaults(func=_cmd_inspect)
    s = sub.add_parser("survey", help="check every map under a directory")
    s.add_argument("levels_dir")
    s.set_defaults(func=_cmd_survey)
    ln = sub.add_parser("learn", help="learn lightshow units from installed maps")
    ln.add_argument("levels_dir")
    ln.add_argument("out")
    ln.set_defaults(func=_cmd_learn)
    g = sub.add_parser("gen-url", help="request generation from a song URL")
    g.add_argument("url")
    g.add_argument("--api", default=DEFAULT_API)
    g.set_defaults(func=_cmd_gen_url)
    sa = sub.add_parser("scan-api", help="ask the running API to scan one map")
    sa.add_argument("map_id")
    sa.add_argument("--api", default=DEFAULT_API)
    sa.set_defaults(func=_cmd_scan_api)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
