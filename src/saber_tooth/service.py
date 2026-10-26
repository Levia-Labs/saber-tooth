"""Service layer: library refresh, scan, generate, apply and learn."""

import hashlib
import shutil
import uuid
from collections.abc import Callable
from pathlib import Path

from saber_tooth.analyser_client import AnalyserClient, AnalyserError
from saber_tooth.analysis import Analysis
from saber_tooth.assemble import assemble_new, folder_name
from saber_tooth.checks import Finding, run_checks
from saber_tooth.fixer import OpConflict, apply_ops, op_from_dict, propose
from saber_tooth.fixer.ops import Fill, Op
from saber_tooth.lightshow import Templates
from saber_tooth.lightshow import learn as learn_templates
from saber_tooth.mapio import MapParseError, load_map, write_map
from saber_tooth.mapio.errors import safe_name
from saber_tooth.model import DIFFICULTIES, Beatmap
from saber_tooth.safe_fs import LevelsWriter
from saber_tooth.store import Store

SUFFIX = " [saber-tooth]"
STAGING_PREFIX = "staging:"
CREATE_MAP = "create-map"
EPS = 1e-6

Span = tuple[str, float, float]


class ApplyConflict(Exception):
    """Approved proposals cannot be applied; nothing was written."""

    def __init__(self, message: str, ids: list[int]) -> None:
        super().__init__(f"{message} (proposals: {ids})" if ids else message)
        self.ids = ids


def map_id_for(folder: str) -> str:
    return hashlib.sha1(folder.encode("utf-8")).hexdigest()[:12]  # noqa: S324 - id, not security


def _local_key(f: Finding) -> tuple:
    notes = sorted((n.beat, n.x, n.y, int(n.color), int(n.cut)) for n in f.notes)
    return (f.difficulty, f.rule, f.beat_start, f.beat_end, tuple(notes))


try:
    from saber_tooth.fixer import finding_key as _key
except ImportError:  # pragma: no cover - until the fixer lane lands finding_key
    _key = _local_key


def _span(op: Op) -> Span | None:
    if isinstance(op, Fill):
        return (op.difficulty, op.beat_start, op.beat_end)
    note = getattr(op, "note", None)
    if note is None:
        return None
    return (op.difficulty, note.beat, note.beat)


def _overlaps(a: Span, b: Span) -> bool:
    if "*" not in (a[0], b[0]) and a[0] != b[0]:
        return False
    return a[1] <= b[2] + EPS and b[1] <= a[2] + EPS


class Service:
    def __init__(
        self,
        levels: Path,
        data: Path,
        store: Store,
        client: AnalyserClient,
        encode: Callable[[Path, Path], None],
    ) -> None:
        self.levels = Path(levels)
        self.data = Path(data)
        self.store = store
        self.client = client
        self.encode = encode

    # library -----------------------------------------------------------------

    def refresh_library(self) -> int:
        count = 0
        for folder in sorted(p for p in self.levels.iterdir() if p.is_dir()):
            if folder.name.startswith("."):
                continue
            mid = map_id_for(folder.name)
            try:
                i = load_map(folder).info
                self.store.upsert_map(mid, folder.name, i.song_name, i.mapper, i.environment, None)
            except (MapParseError, OSError) as exc:
                self.store.upsert_map(mid, folder.name, folder.name, "", "", str(exc))
            count += 1
        return count

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
            raise KeyError(f"unknown map: {map_id}")
        name = rows[0]["folder"]
        folder = (self.levels / name).resolve()
        if Path(name).name != name or folder.parent != self.levels.resolve():
            raise ValueError(f"invalid map folder: {name!r}")
        return folder

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
        bm = load_map(folder)
        analysis = self._analyse(map_id, bm, folder)
        templates = self._templates()
        seed = int(map_id[:8], 16)
        proposals = []
        for finding in run_checks(bm, analysis):
            p = propose(bm, finding, analysis, templates, seed)
            if p is not None:
                proposals.append(p.to_dict())
        self.store._exec("DELETE FROM proposals WHERE map_id=? AND status='pending'", (map_id,))
        self.store.add_proposals(map_id, proposals)
        return len(proposals), analysis is not None

    def scan(self, map_id: str) -> int:
        return self._scan(map_id)[0]

    def run_scan(self, map_id: str) -> dict:
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
        ids = self.store.add_proposals(map_id, [proposal])
        return map_id, ids[0]

    def generate(self, url_or_path: str) -> int:
        return self._generate(url_or_path)[1]

    def run_generate(self, url_or_path: str) -> dict:
        map_id, pid = self._generate(url_or_path)
        return {"map_id": map_id, "proposal": pid}

    # apply -------------------------------------------------------------------

    def apply(self, map_id: str) -> Path:
        approved = self.store.approved(map_id)
        if not approved:
            raise ApplyConflict("no approved proposals to apply", [])
        if map_id.startswith(STAGING_PREFIX):
            target = self._commit_staged(approved)
        else:
            target = self._apply_fixes(map_id, approved)
        for p in approved:
            self.store.set_status(p["id"], "applied")
        self.refresh_library()
        return target

    def run_apply(self, map_id: str) -> dict:
        return {"map_id": map_id, "folder": self.apply(map_id).name}

    def _related(self, spans: list[Span], approved: list[dict]) -> list[int]:
        ids = []
        for p in approved:
            mine = [s for s in (_span(op_from_dict(o)) for o in p["ops"]) if s]
            if any(_overlaps(a, b) for a in mine for b in spans):
                ids.append(p["id"])
        return ids

    def _fixed(self, bm: Beatmap, approved: list[dict]) -> Beatmap:
        cur = bm
        for n, p in enumerate(approved):
            ops = [op_from_dict(o) for o in p["ops"]]
            try:
                cur = apply_ops(cur, ops)
            except OpConflict as exc:
                spans = [s for s in map(_span, ops) if s]
                ids = self._related(spans, approved[: n + 1])
                raise ApplyConflict(f"proposals conflict: {exc}", ids or [p["id"]]) from exc
        return cur

    def _verify(self, original: Beatmap, fixed: Beatmap, approved: list[dict]) -> None:
        all_ids = [p["id"] for p in approved]
        missing = [d for d in DIFFICULTIES if d not in fixed.difficulties]
        if missing:
            raise ApplyConflict(
                f"result lacks difficulties {', '.join(missing)}; approve add-difficulty "
                "proposals first",
                all_ids,
            )
        known = {_key(f) for f in run_checks(original)}
        bad = [f for f in run_checks(fixed) if f.severity == "error" or _key(f) not in known]
        if bad:
            spans = [(f.difficulty, f.beat_start, f.beat_end) for f in bad]
            first = bad[0]
            raise ApplyConflict(
                f"result has {len(bad)} new or remaining problems; first: {first.rule} "
                f"{first.difficulty} @ {first.beat_start:g}: {first.message}",
                self._related(spans, approved) or all_ids,
            )

    def _apply_fixes(self, map_id: str, approved: list[dict]) -> Path:
        folder = self._folder(map_id)
        original = load_map(folder)
        fixed = self._fixed(original, approved)
        self._verify(original, fixed, approved)
        fixed.info.song_name += SUFFIX
        writer = LevelsWriter(self.levels)
        name = writer.unique_name(folder.name + SUFFIX)
        partial = writer.new_folder(name)
        try:
            write_map(fixed, partial, folder)
            for src in sorted(p for p in folder.rglob("*") if p.is_file()):
                rel = src.relative_to(folder)
                dest = partial / rel
                if src.suffix.lower() == ".dat" or dest.exists():
                    continue
                writer.guard(dest)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
            return writer.commit(partial, name)
        except BaseException:
            shutil.rmtree(partial, ignore_errors=True)
            raise

    def _commit_staged(self, approved: list[dict]) -> Path:
        proposal = next((p for p in approved if p["rule"] == CREATE_MAP), None)
        if proposal is None:
            raise ApplyConflict("no approved create-map proposal", [p["id"] for p in approved])
        root = (self.data / "staging").resolve()
        staging = Path(proposal["after"]["staging"]).resolve()
        if staging.parent != root or not staging.is_dir():
            raise ApplyConflict("staging folder is missing", [proposal["id"]])
        writer = LevelsWriter(self.levels)
        name = writer.unique_name(folder_name(proposal["after"]["title"]))
        partial = writer.new_folder(name)
        try:
            for src in sorted(p for p in staging.rglob("*") if p.is_file()):
                dest = partial / src.relative_to(staging)
                writer.guard(dest)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
            target = writer.commit(partial, name)
        except BaseException:
            shutil.rmtree(partial, ignore_errors=True)
            raise
        shutil.rmtree(staging, ignore_errors=True)
        return target
