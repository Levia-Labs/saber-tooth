"""Service layer: library refresh, scan, generate, apply and learn."""

import hashlib
import logging
import shutil
import threading
import uuid
from collections.abc import Callable
from pathlib import Path

from saber_tooth.analyser_client import AnalyserClient, AnalyserError
from saber_tooth.analysis import Analysis, read_project
from saber_tooth.assemble import assemble_new, folder_name
from saber_tooth.checks import run_checks
from saber_tooth.fixer import OpConflict, apply_ops, new_findings, op_from_dict, propose
from saber_tooth.lightshow import Templates
from saber_tooth.lightshow import learn as learn_templates
from saber_tooth.mapio import MapParseError, load_map
from saber_tooth.mapio.errors import safe_name
from saber_tooth.model import DIFFICULTIES, Beatmap
from saber_tooth.service.errors import ApplyConflict, MapNotFound, MapUnreadable
from saber_tooth.service.util import finding_from_dict, map_id_for, related, span
from saber_tooth.service.writeout import commit_staged, write_fixed
from saber_tooth.store import Store

log = logging.getLogger(__name__)

SUFFIX = " [saber-tooth]"
STAGING_PREFIX = "staging:"
CREATE_MAP = "create-map"


class Service:
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
        with self._lock:
            self.refresh_library()
        return True

    def refresh_library(self) -> int:
        self._seen = self._listing()
        seen: set[str] = set()
        for folder in sorted(self.levels.iterdir()):
            if folder.name.startswith(".") or folder.is_symlink() or not folder.is_dir():
                continue
            mid = map_id_for(folder.name)
            seen.add(mid)
            try:
                i = load_map(folder).info
                self.store.upsert_map(mid, folder.name, i.song_name, i.mapper, i.environment, None)
            except (MapParseError, OSError) as exc:
                self.store.upsert_map(mid, folder.name, folder.name, "", "", str(exc))
        self.store.prune_maps(seen)
        self._clean_staging()
        return len(seen)

    def _clean_staging(self) -> None:
        root = self.data / "staging"
        if not root.is_dir():
            return
        for d in root.iterdir():
            props = self.store.proposals(f"{STAGING_PREFIX}{d.name}")
            if props and all(p["status"] in ("rejected", "applied") for p in props):
                shutil.rmtree(d, ignore_errors=True)

    def _templates(self) -> Templates | None:
        path = self.data / "templates.json"
        return Templates.load(path) if path.is_file() else None

    def learn(self) -> int:
        templates = learn_templates(self.levels)
        self.data.mkdir(parents=True, exist_ok=True)
        templates.save(self.data / "templates.json")
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
        except (AnalyserError, ValueError, MapParseError):
            return None

    def _scan(self, map_id: str) -> tuple[int, bool]:
        folder = self._folder(map_id)
        bm = self._load(folder)
        analysis = self._analyse(map_id, bm, folder)
        templates = self._templates()
        seed = int(map_id[:8], 16)
        findings = run_checks(bm, analysis)
        proposals = []
        for finding in findings:
            p = propose(bm, finding, analysis, templates, seed)
            if p is not None:
                proposals.append(p.to_dict())
        project = analysis.audio.parent.name if analysis and analysis.audio else None
        scan = {"findings": [f.to_dict() for f in findings], "analysis": project}
        self.store.replace_open_proposals(map_id, proposals, scan)
        return len(proposals), analysis is not None

    def scan(self, map_id: str) -> int:
        with self._lock:
            return self._scan(map_id)[0]

    def run_scan(self, map_id: str) -> dict:
        with self._lock:
            count, analysed = self._scan(map_id)
        return {"map_id": map_id, "proposals": count, "analysis": analysed}

    # generate ----------------------------------------------------------------

    def _generate(self, url_or_path: str) -> tuple[str, int]:
        if url_or_path.startswith(("http://", "https://")):
            a = self.client.analyse_url(url_or_path)
        else:
            src = Path(url_or_path)
            a = self.client.analyse_file(src, src.name)
        token = uuid.uuid4().hex
        staging = self.data / "staging" / token
        staging.parent.mkdir(parents=True, exist_ok=True)
        seed = int(hashlib.sha1(a.name.encode("utf-8")).hexdigest()[:8], 16)  # noqa: S324
        assemble_new(a, self._templates(), staging, seed, self.encode)
        proposal = {
            "rule": CREATE_MAP,
            "difficulty": "*",
            "severity": "warn",
            "summary": f"Create new map: {a.name}",
            "ops": [],
            "before": [],
            "after": {"staging": str(staging), "title": a.name},
        }
        map_id = f"{STAGING_PREFIX}{token}"
        try:
            ids = self.store.add_proposals(map_id, [proposal])
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return map_id, ids[0]

    def generate(self, url_or_path: str) -> int:
        return self._generate(url_or_path)[1]

    def run_generate(self, url_or_path: str) -> dict:
        map_id, pid = self._generate(url_or_path)
        return {"map_id": map_id, "proposal": pid}

    # apply -------------------------------------------------------------------

    def apply(self, map_id: str) -> Path:
        with self._lock:
            if not map_id.startswith(STAGING_PREFIX):
                self._folder(map_id)
            approved = self.store.approved(map_id)
            if not approved:
                raise ApplyConflict("no approved proposals to apply", [])
            if map_id.startswith(STAGING_PREFIX):
                target = self._commit_staged(approved)
            else:
                target = self._apply_fixes(map_id, approved)
            self.store.mark_applied([p["id"] for p in approved])
            try:
                self.refresh_library()
            except Exception:
                log.exception("library refresh failed after applying %s", map_id)
            return target

    def run_apply(self, map_id: str) -> dict:
        return {"map_id": map_id, "folder": self.apply(map_id).name}

    def _fixed(self, bm: Beatmap, approved: list[dict]) -> Beatmap:
        cur = bm
        for n, p in enumerate(approved):
            try:
                ops = [op_from_dict(o) for o in p["ops"]]
                cur = apply_ops(cur, ops)
            except OpConflict as exc:
                spans = [s for s in map(span, ops) if s]
                ids = related(spans, approved[: n + 1])
                raise ApplyConflict(f"proposals conflict: {exc}", ids or [p["id"]]) from exc
            except (KeyError, ValueError, TypeError) as exc:
                raise ApplyConflict(f"proposal is unreadable: {exc}", [p["id"]]) from exc
        return cur

    def _stored_analysis(self, info: dict | None) -> Analysis | None:
        name = info["analysis"] if info else None
        if not name or self.uploads is None:
            return None
        root = Path(self.uploads).resolve()
        folder = (root / name).resolve()
        if folder.parent != root:
            return None
        try:
            return read_project(folder)
        except (OSError, KeyError, ValueError):
            return None

    def _verify(self, map_id: str, original: Beatmap, fixed: Beatmap, approved: list[dict]) -> None:
        all_ids = [p["id"] for p in approved]
        missing = [d for d in DIFFICULTIES if d not in fixed.difficulties]
        if missing:
            raise ApplyConflict(
                f"result lacks difficulties {', '.join(missing)}; approve add-difficulty "
                "proposals first",
                all_ids,
            )
        info = self.store.scan_info(map_id)
        if info is not None:
            known = [finding_from_dict(d) for d in info["findings"]]
        else:
            known = run_checks(original)
        analysis = self._stored_analysis(info)
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

    def _apply_fixes(self, map_id: str, approved: list[dict]) -> Path:
        folder = self._folder(map_id)
        original = self._load(folder)
        fixed = self._fixed(original, approved)
        self._verify(map_id, original, fixed, approved)
        fixed.info.song_name += SUFFIX
        return write_fixed(self.levels, folder, fixed, folder.name + SUFFIX)

    def _commit_staged(self, approved: list[dict]) -> Path:
        proposal = next((p for p in approved if p["rule"] == CREATE_MAP), None)
        if proposal is None:
            raise ApplyConflict("no approved create-map proposal", [p["id"] for p in approved])
        root = (self.data / "staging").resolve()
        staging = Path(proposal["after"]["staging"]).resolve()
        if staging.parent != root or not staging.is_dir():
            raise ApplyConflict("staging folder is missing", [proposal["id"]])
        target = commit_staged(self.levels, staging, folder_name(proposal["after"]["title"]))
        shutil.rmtree(staging, ignore_errors=True)
        return target
