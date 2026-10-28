"""Service layer: library refresh, scan, apply and learn."""

import logging
import threading
from collections.abc import Callable
from pathlib import Path

from saber_tooth.analyser_client import AnalyserClient, AnalyserError
from saber_tooth.analysis import Analysis
from saber_tooth.audio import probe_tags
from saber_tooth.checks import run_checks
from saber_tooth.fixer import propose
from saber_tooth.lightshow import BUNDLED, Templates
from saber_tooth.lightshow import learn as learn_templates
from saber_tooth.mapio import MapParseError, load_map
from saber_tooth.mapio.errors import safe_name
from saber_tooth.model import Beatmap
from saber_tooth.service.delete import DeleteMixin
from saber_tooth.service.duration import folder_duration
from saber_tooth.service.errors import ApplyConflict, MapNotFound, MapUnreadable
from saber_tooth.service.lightshow_set import LEARNED, active_templates
from saber_tooth.service.lightshow_set import info as lightshow_info
from saber_tooth.service.ordered import Outcome, apply_in_order
from saber_tooth.service.util import map_id_for
from saber_tooth.service.verify import stored_analysis, verify
from saber_tooth.service.writeout import write_fixed
from saber_tooth.store import Store
from saber_tooth.store_maps import level_mask

log = logging.getLogger(__name__)

SUFFIX = " [saber-tooth]"
APPLY_RETRIES = 3


class _Stale(Exception):
    """The approved set changed between reading it and writing the result."""


class Service(DeleteMixin):
    bundled: Path | None = BUNDLED  # tests may point this elsewhere
    probe_tags = staticmethod(probe_tags)

    def __init__(
        self,
        levels: Path,
        data: Path,
        store: Store,
        client: AnalyserClient,
        encode: Callable[[Path, Path], None],
        uploads: Path | None = None,
    ) -> None:
        self.levels = Path(levels)
        self.data = Path(data)
        self.store = store
        self.client = client
        self.encode = encode
        self.uploads = Path(uploads) if uploads else getattr(client, "uploads", None)
        self._lock = threading.Lock()
        self._refresh_lock = threading.Lock()  # one re-index at a time; readers never wait on it
        self._seen: frozenset[str] = frozenset()

    # library -----------------------------------------------------------------

    def _listing(self) -> frozenset[str]:
        return frozenset(
            p.name
            for p in self.levels.iterdir()
            if not p.name.startswith(".") and not p.is_symlink() and p.is_dir()
        )

    def refresh_if_changed(self) -> bool:
        """Re-index when the set of folders under levels differs from the last refresh."""
        try:
            if self._listing() == self._seen:
                return False
        except OSError:
            return False
        return self.refresh_library(wait=False) is not None

    def refresh_library(self, wait: bool = True) -> int | None:
        """Re-index the library; with wait=False, None when another re-index is running."""
        if not self._refresh_lock.acquire(blocking=wait):
            return None  # readers then serve the store as it is
        try:
            return self._reindex()
        finally:
            self._refresh_lock.release()

    def _reindex(self) -> int:
        self._seen = self._listing()
        seen: set[str] = set()
        for folder in sorted(self.levels.iterdir()):
            if folder.name.startswith(".") or folder.is_symlink() or not folder.is_dir():
                continue
            mid = map_id_for(folder.name)
            seen.add(mid)
            try:
                beatmap = load_map(folder)
                i = beatmap.info
                self.store.upsert_map(
                    mid, folder.name, i.song_name, i.mapper, i.environment, None,
                    i.bpm, folder_duration(folder, beatmap), level_mask(beatmap.difficulties),
                )  # fmt: skip
            except (MapParseError, OSError) as exc:
                self.store.upsert_map(mid, folder.name, folder.name, "", "", str(exc))
        self.store.prune_maps(seen)
        return len(seen)

    def _templates(self) -> Templates | None:
        return active_templates(self.data, self.bundled)

    def lightshow_info(self) -> dict:
        return lightshow_info(self.data, self.bundled)

    def learn(self) -> int:
        templates = learn_templates(self.levels)
        self.data.mkdir(parents=True, exist_ok=True)
        tmp = self.data / f"{LEARNED}.tmp"
        templates.save(tmp)
        tmp.replace(self.data / LEARNED)
        return sum(len(units) for units in templates.units.values())

    def _folder(self, map_id: str) -> Path:
        rows = [m for m in self.store.list_maps() if m["id"] == map_id]
        if not rows:
            raise MapNotFound(f"unknown map: {map_id}")
        name = rows[0]["folder"]
        folder = self.levels / name
        if Path(name).name != name or folder.is_symlink() or not folder.is_dir():
            raise MapNotFound(f"map folder is gone: {name}")
        if rows[0]["parse_error"]:
            raise MapUnreadable(f"map {name} cannot be read: {rows[0]['parse_error']}")
        return folder

    def _load(self, folder: Path) -> Beatmap:
        try:
            return load_map(folder)
        except (MapParseError, OSError) as exc:
            raise MapUnreadable(f"map {folder.name} cannot be read: {exc}") from exc

    # scan --------------------------------------------------------------------

    def _analyse(self, map_id: str, bm: Beatmap, folder: Path) -> Analysis | None:
        try:
            audio = folder / safe_name(bm.info.song_file)
            if not audio.is_file():
                return None
            return self.client.analyse_file(audio, f"{map_id}.ogg")
        except (AnalyserError, ValueError, MapParseError, OSError, KeyError):
            return None

    def _scan(self, map_id: str) -> tuple[int, bool]:
        folder = self._folder(map_id)
        bm = self._load(folder)
        analysis = self._analyse(map_id, bm, folder)  # slow HTTP call: the lock is not held
        templates = self._templates()
        seed = int(map_id[:8], 16)
        findings = run_checks(bm, analysis)
        proposals = []
        for finding in findings:
            p = propose(bm, finding, analysis, templates, seed)
            if p is not None:
                proposals.append({**p.to_dict(), "finding": finding.to_dict()})
        project = analysis.audio.parent.name if analysis and analysis.audio else None
        scan = {"findings": [f.to_dict() for f in findings], "analysis": project}
        with self._lock:
            self.store.replace_open_proposals(map_id, proposals, scan)
        return len(proposals), analysis is not None

    def scan(self, map_id: str) -> int:
        return self._scan(map_id)[0]

    def run_scan(self, map_id: str) -> dict:
        count, analysed = self._scan(map_id)
        return {"map_id": map_id, "proposals": count, "analysis": analysed}

    # apply -------------------------------------------------------------------

    def apply(self, map_id: str) -> Path:
        return self._apply(map_id)[0]

    def _apply(self, map_id: str) -> tuple[Path, Outcome]:
        with self._lock:
            self._folder(map_id)
            for _ in range(APPLY_RETRIES):
                approved = self.store.approved(map_id)
                if not approved:
                    raise ApplyConflict("no approved proposals to apply", [])
                ids = [p["id"] for p in approved]
                try:
                    target, outcome = self._write(map_id, approved)
                except _Stale:  # a proposal was rejected mid-apply: redo without it
                    continue
                except BaseException:
                    self.store.release(ids)  # the claim taken by unchanged() is given back
                    raise
                break
            else:
                raise ApplyConflict("proposals kept changing during apply; retry", [])
            self.store.mark_applied(outcome.applied)
            try:
                self.refresh_library()
            except Exception:
                log.exception("library refresh failed after applying %s", map_id)
            return target, outcome

    def _write(self, map_id: str, approved: list[dict]) -> tuple[Path, Outcome]:
        def unchanged(ids: list[int]) -> None:
            if {p["id"] for p in self.store.approved(map_id)} != set(ids):
                raise _Stale
            if not self.store.claim(ids):  # from here a reject gets 409 until written
                raise _Stale

        return self._apply_fixes(map_id, approved, unchanged)

    def run_apply(self, map_id: str) -> dict:
        target, outcome = self._apply(map_id)
        return {"map_id": map_id, "folder": target.name, **outcome.to_dict()}

    def _apply_fixes(
        self, map_id: str, approved: list[dict], unchanged: Callable[[list[int]], None]
    ) -> tuple[Path, Outcome]:
        folder = self._folder(map_id)
        original = self._load(folder)
        analysis = stored_analysis(self.uploads, self.store.scan_info(map_id))
        seed, templates = int(map_id[:8], 16), self._templates()
        fixed, kept, outcome = apply_in_order(
            self.store, map_id, original, approved, analysis, templates, seed
        )
        if not kept:
            msg = "every approved proposal was superseded; review the new proposals"
            raise ApplyConflict(msg, outcome.superseded)
        verify(self.store, self.uploads, map_id, original, fixed, kept)
        fixed.info.song_name += SUFFIX
        unchanged(outcome.applied)
        target = write_fixed(self.levels, folder, fixed, folder.name + SUFFIX)
        return target, outcome
