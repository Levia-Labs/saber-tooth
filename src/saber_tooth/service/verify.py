"""Applying approved proposals: replay the ops, then verify the result."""

from pathlib import Path

from saber_tooth.analysis import Analysis, read_project
from saber_tooth.checks import run_checks
from saber_tooth.fixer import new_findings
from saber_tooth.model import DIFFICULTIES, Beatmap
from saber_tooth.service.errors import ApplyConflict
from saber_tooth.service.util import finding_from_dict, related
from saber_tooth.store import Store


def stored_analysis(uploads: Path | None, info: dict | None) -> Analysis | None:
    name = info["analysis"] if info else None
    if not name or uploads is None:
        return None
    root = Path(uploads).resolve()
    folder = (root / name).resolve()
    if folder.parent != root:
        return None
    try:
        return read_project(folder)
    except (OSError, KeyError, ValueError):
        return None


def verify(
    store: Store,
    uploads: Path | None,
    map_id: str,
    original: Beatmap,
    fixed: Beatmap,
    approved: list[dict],
) -> None:
    all_ids = [p["id"] for p in approved]
    missing = [d for d in DIFFICULTIES if d not in fixed.difficulties]
    if missing:
        raise ApplyConflict(
            f"result lacks difficulties {', '.join(missing)}; approve add-difficulty "
            "proposals first",
            all_ids,
        )
    info = store.scan_info(map_id)
    if info is not None:
        known = [finding_from_dict(d) for d in info["findings"]]
    else:
        known = run_checks(original)
    analysis = stored_analysis(uploads, info)
    after = run_checks(fixed, analysis)
    bad = [f for f in after if f.severity == "error"]
    bad += [f for f in new_findings(after, known) if f not in bad]
    if bad:
        spans = [(f.difficulty, f.beat_start, f.beat_end) for f in bad]
        first = bad[0]
        raise ApplyConflict(
            f"result has {len(bad)} new or remaining problems; first: {first.rule} "
            f"{first.difficulty} @ {first.beat_start:g}: {first.message}",
            related(spans, approved) or all_ids,
        )
