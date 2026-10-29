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
        learn=lambda p=None: 3,
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
    assert calls[0] == ("scan", ("m1", noop), {})
    assert calls[2] == ("fix", ("m1",), {"progress": noop})
    assert calls[3] == ("crop", ("m1", 4.0, 68.0, True), {"progress": noop})
    assert calls[4] == ("generate", ("https://youtu.be/x", noop), {})


def test_generate_from_upload_runs_and_removes_the_folder(tmp_path: Path) -> None:
    box = tmp_path / "uploads" / "abc"
    box.mkdir(parents=True)
    song = box / "song.mp3"
    song.write_bytes(b"x")
    calls: list = []
    sink = lambda t: None  # noqa: E731
    core_handlers(_service(tmp_path, calls))["generate"]({"upload": str(song)}, sink)
    assert calls == [("generate", (str(song.resolve()), sink), {})]
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
