### Task 3: Handlers for every job kind and Fix round progress

**Files:**

- Create: `src/saber_tooth/api/jobs_api.py`
- Modify: `src/saber_tooth/api/core.py` (constructor line 80; `scan`, `apply`, `fix`, `learn`, `generate_url`, `generate_file` lines 222-259)
- Modify: `src/saber_tooth/api/crop_api.py` (lines 74-77)
- Modify: `src/saber_tooth/api/beatsaver.py` (constructor line 83, `download` line 220)
- Modify: `src/saber_tooth/api/__init__.py` (after `crop_api = CropApi(api)`, line 62)
- Modify: `src/saber_tooth/service/fix.py` (`fix_beatmap` line 47, loop line 61, `fix_map` line 90)
- Modify: `src/saber_tooth/api/README.md`
- Test: `tests/test_jobs_handlers.py` (new)

**Interfaces:**

- Consumes: `Jobs.register`, `Jobs.submit`, `Jobs.start` (Task 2).
- Produces:
  - `jobs_api.UPLOAD_GONE = "the uploaded file is no longer available; upload it again"`
  - `jobs_api.core_handlers(service) -> dict[str, Handler]` for `scan`, `apply`, `fix`, `learn`, `generate`, `crop`
  - `jobs_api.upload_path(data: Path, raw: object) -> Path | None`
  - Job arguments per kind: scan, apply, fix `{"map_id"}`; crop `{"map_id", "start", "end", "replace"}`; generate `{"url"}` or `{"upload"}`; learn `{}`; bs-download `{"ids"}`
  - `fix_beatmap(..., on_round: Callable[[int, int], None] | None = None)`; `fix_map(svc, map_id, max_rounds=MAX_ROUNDS, progress: Callable[[str], None] | None = None)`

- [ ] **Step 1: Write the failing tests**

`tests/test_jobs_handlers.py`:

```python
from pathlib import Path
from types import SimpleNamespace

from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.api.jobs_api import UPLOAD_GONE, core_handlers, upload_path
from saber_tooth.jobs import Jobs
from saber_tooth.store import Store


def _service(tmp_path: Path, calls: list):
    def record(name):
        return lambda *a, **k: calls.append((name, a, k)) or {"ok": name}

    return SimpleNamespace(
        data=tmp_path,
        run_scan=record("scan"),
        run_apply=record("apply"),
        fix_map=record("fix"),
        learn=lambda: 3,
        run_generate=record("generate"),
        crop_map=record("crop"),
    )


def test_handlers_call_the_service_with_stored_args(tmp_path: Path) -> None:
    calls: list = []
    h = core_handlers(_service(tmp_path, calls))
    noop = lambda text: None  # noqa: E731  # progress sink
    h["scan"]({"map_id": "m1"}, noop)
    h["apply"]({"map_id": "m1"}, noop)
    h["fix"]({"map_id": "m1"}, noop)
    h["crop"]({"map_id": "m1", "start": 4.0, "end": 68.0, "replace": True}, noop)
    h["generate"]({"url": "https://youtu.be/x"}, noop)
    assert h["learn"]({}, noop) == {"units": 3}
    assert calls[0] == ("scan", ("m1",), {})
    assert calls[2] == ("fix", ("m1",), {"progress": noop})
    assert calls[3] == ("crop", ("m1", 4.0, 68.0, True), {})
    assert calls[4] == ("generate", ("https://youtu.be/x",), {})


def test_generate_from_upload_runs_and_removes_the_folder(tmp_path: Path) -> None:
    box = tmp_path / "uploads" / "abc"
    box.mkdir(parents=True)
    song = box / "song.mp3"
    song.write_bytes(b"x")
    calls: list = []
    core_handlers(_service(tmp_path, calls))["generate"]({"upload": str(song)}, lambda t: None)
    assert calls == [("generate", (str(song.resolve()),), {})]
    assert not box.exists()


def test_generate_from_a_vanished_upload_fails_with_the_message(tmp_path: Path) -> None:
    gone = tmp_path / "uploads" / "abc" / "song.mp3"
    calls: list = []
    try:
        core_handlers(_service(tmp_path, calls))["generate"]({"upload": str(gone)}, lambda t: 0)
    except FileNotFoundError as exc:
        assert str(exc) == UPLOAD_GONE
    else:
        raise AssertionError("expected FileNotFoundError")
    assert calls == []


@given(st.text(max_size=80))
def test_upload_path_never_leaves_the_uploads_folder(tmp_path_factory, raw: str) -> None:
    data = tmp_path_factory.mktemp("data")
    root = (data / "uploads").resolve()
    path = upload_path(data, raw)
    assert path is None or path.parent.parent == root


def test_upload_outside_uploads_is_refused_and_nothing_deleted(tmp_path: Path) -> None:
    outside = tmp_path / "levels" / "keep" / "song.mp3"
    outside.parent.mkdir(parents=True)
    outside.write_bytes(b"x")
    calls: list = []
    try:
        core_handlers(_service(tmp_path, calls))["generate"]({"upload": str(outside)}, lambda t: 0)
    except FileNotFoundError as exc:
        assert str(exc) == UPLOAD_GONE
    assert outside.exists() and calls == []


def test_a_map_deleted_while_queued_fails_and_the_worker_continues(tmp_path: Path) -> None:
    store = Store(tmp_path / "db.sqlite")
    jobs = Jobs(store)

    def scan(args, progress):
        raise LookupError(f"unknown map: {args['map_id']}")

    jobs.register("scan", scan)
    jobs.register("learn", lambda args, progress: {"units": 1})
    try:
        gone = jobs.submit("scan", {"map_id": "dead"}, map_id="dead")
        after = jobs.submit("learn")
        assert jobs.wait(gone)["error"] == "unknown map: dead"
        assert jobs.wait(after)["status"] == "done"
        assert store.job_lists()["recent"][1]["map_exists"] is False
    finally:
        jobs.shutdown()
```

Hypothesis note: `tmp_path_factory` is session scoped, so the `@given` test may use it; if the repo's hypothesis profile warns about function-scoped fixtures, this one avoids that.

Also add, to the existing Fix tests (search `tests/` for `fix_beatmap(`), one test that `fix_beatmap(..., on_round=calls.append_pair)` reports `(1, max_rounds)` first and one call per round run, with `max_rounds=2`, built from the same fixture map those tests already use.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `task st:test -- tests/test_jobs_handlers.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'saber_tooth.api.jobs_api'`.

- [ ] **Step 3: Implement**

`src/saber_tooth/api/jobs_api.py` (Task 4 adds the list, view and cancel functions to this file):

```python
"""Job handlers per kind, and the job list, view and cancel behind /api/jobs."""

import shutil
from pathlib import Path

from saber_tooth.jobs import Handler

UPLOAD_GONE = "the uploaded file is no longer available; upload it again"


def upload_path(data: Path, raw: object) -> Path | None:
    """The stored upload path when it sits in `data/uploads/<box>/`; anything else is refused."""
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        return None
    root = (Path(data) / "uploads").resolve()
    try:
        path = Path(raw).resolve()
    except (OSError, ValueError):
        return None
    return path if path.parent.parent == root else None


def _generate(service, args: dict) -> dict:
    if "url" in args:
        return service.run_generate(args["url"])
    path = upload_path(service.data, args.get("upload"))
    if path is None:
        raise FileNotFoundError(UPLOAD_GONE)
    try:
        if not path.is_file():
            raise FileNotFoundError(UPLOAD_GONE)
        return service.run_generate(str(path))
    finally:
        shutil.rmtree(path.parent, ignore_errors=True)


def core_handlers(service) -> dict[str, Handler]:
    return {
        "scan": lambda a, p: service.run_scan(a["map_id"]),
        "apply": lambda a, p: service.run_apply(a["map_id"]),
        "fix": lambda a, p: service.fix_map(a["map_id"], progress=p),
        "learn": lambda a, p: {"units": service.learn()},
        "generate": lambda a, p: _generate(service, a),
        "crop": lambda a, p: service.crop_map(a["map_id"], a["start"], a["end"], a["replace"]),
    }
```

Check before writing: `api/upload.py` saves to `service.data / "uploads" / <uuid hex> / <file>` (`upload.py:62-66`, called with `service.data` at `api/__init__.py:159`); `upload_path` relies on that two-level layout.

`src/saber_tooth/api/core.py`:

1. Constructor: after `self.jobs = Jobs(service.store)` add
   ```python
   for kind, handler in core_handlers(service).items():
       self.jobs.register(kind, handler)
   ```
   with `from saber_tooth.api.jobs_api import core_handlers`.
2. `scan`: `self.jobs.submit("scan", {"map_id": map_id}, map_id=map_id, dedupe=True)`; same for `apply` and `fix` with their kinds.
3. `learn`: `self.jobs.submit("learn")`.
4. `generate_url`: `self.jobs.submit("generate", {"url": url})`.
5. `generate_file`:
   ```python
   def generate_file(self, path: Path) -> dict:
       try:
           return {"job": self.jobs.submit("generate", {"upload": str(path)})}
       except BaseException:
           shutil.rmtree(path.parent, ignore_errors=True)
           raise
   ```
   Every method keeps returning `{"job": <id>}`.

`src/saber_tooth/api/crop_api.py` lines 74-77 become:

```python
        args = {"map_id": map_id, "start": start, "end": end, "replace": replace}
        return {"job": self.api.jobs.submit("crop", args, map_id=map_id)}
```

`src/saber_tooth/api/beatsaver.py`: at the end of `BeatSaverApi.__init__` add `api.jobs.register("bs-download", lambda a, p: self._download_job(a["ids"]))`; `download` becomes `return {"job": self.api.jobs.submit("bs-download", {"ids": ids})}`. The file is at 290 lines; keep the net change at or under +2 lines.

`src/saber_tooth/api/__init__.py`, right after `crop_api = CropApi(api)`:

```python
    api.jobs.start()  # after every handler is registered, so resumed rows find theirs
```

`src/saber_tooth/service/fix.py`:

1. `fix_beatmap` gains a last parameter `on_round: Callable[[int, int], None] | None = None`; first statement inside the `for n in range(1, max_rounds + 1):` loop: `if on_round: on_round(n, max_rounds)`.
2. `fix_map(svc, map_id: str, max_rounds: int = MAX_ROUNDS, progress: Callable[[str], None] | None = None)`; the call becomes
   ```python
   on_round = (lambda n, total: progress(f"round {n} of {total}")) if progress else None
   run = fix_beatmap(original, analysis, svc._templates(), int(map_id[:8], 16), max_rounds, on_round)
   ```
3. `from collections.abc import Callable` if not imported.

- [ ] **Step 4: Run the whole suite**

Run: `task st:test -q`
Expected: PASS. Tests that used `jobs.future(...)` or closures elsewhere (`tests/test_api_crop.py`, `tests/test_crop_replace.py`, `tests/test_delete_map.py`) switch to `api.jobs.wait(job_id)`; change only how they wait, never what they assert.

- [ ] **Step 5: README and commit**

`src/saber_tooth/api/README.md`: add "`jobs_api.py`: the handler for each job kind (scan, apply, fix, learn, generate, crop), upload path checks, and the job list, view and cancel." in its numbered style.

Main thread commits: `task st:commit -- -m "feat(api): every job kind runs through a named handler with stored arguments; Fix reports its round" <every file changed in this task>`

---
