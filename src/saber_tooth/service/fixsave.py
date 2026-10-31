"""Saved progress of a fix: the copy on disk plus a checkpoint naming where the engine stopped."""

import hashlib
import json
from pathlib import Path

from saber_tooth.service.fixrun import FixRun


def source_stamp(folder: Path) -> str:
    """Changes when any file of the source map changes, so an old checkpoint is not reused."""
    h = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        if p.is_file():
            st = p.stat()
            h.update(f"{p.relative_to(folder)}:{st.st_size}:{st.st_mtime_ns}".encode())
    return h.hexdigest()


class Checkpoint:
    """JSON file in the data folder, one per map; removed when the fix finishes."""

    def __init__(self, data: Path, map_id: str) -> None:
        self.path = Path(data) / "fix-checkpoints" / f"{map_id}.json"

    def load(self, stamp: str) -> dict | None:
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return saved if saved.get("stamp") == stamp else None

    def save(self, stamp: str, folder: str, run: FixRun, position: dict, applied: int) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = {
            "stamp": stamp,
            "folder": folder,
            "position": position,
            "completed": run.completed,
            "unfixed": run.unfixed,
            "rounds": run.rounds,
            "applied": applied,
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(body), encoding="utf-8")
        tmp.replace(self.path)

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)


def _window(f: dict) -> tuple:
    return (f.get("rule"), f.get("difficulty"), f.get("beat_start"), f.get("beat_end"))


def with_reasons(findings: list[dict], unfixed: list[dict]) -> list[dict]:
    """Findings with `unfixed_reason` added where Fix left that rule, difficulty and window."""
    why = {_window(u): u["reason"] for u in unfixed if u.get("reason")}
    return [{**f, "unfixed_reason": why[_window(f)]} if _window(f) in why else f for f in findings]
