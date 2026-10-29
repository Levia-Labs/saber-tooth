# ruff: noqa: F811
"""A cancel requested mid-run ends each non-progress job kind cancelled with nothing written."""

import httpx
import pytest
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st

from saber_tooth import api as api_module
from saber_tooth.api.jobs_api import core_handlers
from saber_tooth.fixer import Flip
from saber_tooth.jobs import Jobs
from saber_tooth.service import map_id_for
from saber_tooth.service.lightshow_set import LEARNED
from saber_tooth.service.util import checkpoint
from tests.crop_helpers import NAME as CROP_NAME
from tests.crop_helpers import cuts, make_service  # noqa: F401
from tests.test_api import svc  # noqa: F401
from tests.test_api_beatsaver import Upstream, make_app
from tests.test_service import NAME, NOTE, _hashes, _make, _propose
from tests.test_service import Cut as Cut
from tests.test_service_generate import svc as gen_svc  # noqa: F401


def run_cancelled(svc, kind: str, args: dict, hook) -> dict:
    """Run one job whose handler path calls `cancel()` through `hook(cancel)`; the finished row."""
    jobs = Jobs(svc.store)
    for k, h in core_handlers(svc).items():
        jobs.register(k, h)
    job_id = svc.store.create_job(kind, args.get("map_id"), args)
    hook(lambda: jobs.request_cancel(job_id))
    jobs.start()
    row = jobs.wait(job_id)
    jobs.shutdown()
    return row


def test_scan_cancelled_before_the_save_stores_nothing(tmp_path, monkeypatch):
    svc = _make(tmp_path)
    mid = map_id_for(NAME)

    def hook(cancel):
        monkeypatch.setattr(svc, "_templates", lambda: cancel())  # after the audio analysis

    row = run_cancelled(svc, "scan", {"map_id": mid}, hook)
    assert row["status"] == "cancelled" and row["result"] is None
    assert svc.store.scan_info(mid) is None and svc.store.proposals(mid) == []


def test_apply_cancelled_before_the_write_leaves_the_proposals_approved(tmp_path, monkeypatch):
    svc = _make(tmp_path)
    mid = map_id_for(NAME)
    _propose(svc, mid, [Flip("Hard", NOTE, Cut(0))])
    before = _hashes(svc.levels / NAME)

    def hook(cancel):
        monkeypatch.setattr(svc, "_templates", lambda: cancel())

    row = run_cancelled(svc, "apply", {"map_id": mid}, hook)
    assert row["status"] == "cancelled" and row["error"] is None
    assert sorted(p.name for p in svc.levels.iterdir()) == [NAME]
    assert _hashes(svc.levels / NAME) == before
    assert [p["status"] for p in svc.store.proposals(mid)] == ["approved"]


def test_learn_cancelled_before_the_save_writes_no_templates(tmp_path, monkeypatch):
    import importlib

    learn_mod = importlib.import_module("saber_tooth.lightshow.learn")  # the package shadows it
    svc = _make(tmp_path)
    real = learn_mod.load_map

    def hook(cancel):
        def load(folder):
            cancel()
            return real(folder)

        monkeypatch.setattr(learn_mod, "load_map", load)

    row = run_cancelled(svc, "learn", {}, hook)
    assert row["status"] == "cancelled"
    assert not (svc.data / LEARNED).exists() and not (svc.data / f"{LEARNED}.tmp").exists()


def test_generate_cancelled_mid_build_leaves_no_map_and_no_staging(gen_svc):
    def hook(cancel):
        real = gen_svc.encode

        def encode(wav, egg):
            cancel()
            real(wav, egg)

        gen_svc.encode = encode

    url = {"url": "https://www.youtube.com/watch?v=VKUGl7wR7Dg"}
    row = run_cancelled(gen_svc, "generate", url, hook)
    assert row["status"] == "cancelled" and row["result"] is None
    assert list(gen_svc.levels.iterdir()) == []
    assert not list((gen_svc.data / "staging").iterdir())
    assert gen_svc.store.list_maps() == []


@pytest.mark.parametrize("replace", [False, True])
def test_crop_cancelled_before_the_write_changes_nothing(tmp_path, cuts, monkeypatch, replace):
    from saber_tooth.service import crop as crop_mod

    svc = make_service(tmp_path)
    mid = map_id_for(CROP_NAME)
    window = svc.crop_timeline(mid)["lengths"]["60"]["suggestions"][0]
    before = _hashes(svc.levels / CROP_NAME)
    args = {
        "map_id": mid,
        "start": window["start_beat"],
        "end": window["end_beat"],
        "replace": replace,
    }

    def hook(cancel):
        real = crop_mod.crop_beatmap

        def crop(*a, **kw):
            cancel()
            return real(*a, **kw)

        monkeypatch.setattr(crop_mod, "crop_beatmap", crop)

    row = run_cancelled(svc, "crop", args, hook)
    assert row["status"] == "cancelled" and row["result"] is None
    assert [p.name for p in svc.levels.iterdir()] == [CROP_NAME]
    assert _hashes(svc.levels / CROP_NAME) == before and cuts == []


def test_bs_download_cancelled_after_the_lookup_installs_nothing(svc, monkeypatch):
    made = []
    real_api = api_module.Api
    monkeypatch.setattr(api_module, "Api", lambda s: made.append(real_api(s)) or made[0])
    up = Upstream()
    holder = {}

    def upstream(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/maps/ids/"):
            made[0].jobs.request_cancel(holder["id"])
        return up(request)

    app = make_app(svc, upstream)
    with TestClient(app, base_url="http://localhost"):
        api = made[0]
        before = sorted(p.name for p in svc.levels.iterdir())
        holder["id"] = api.store.create_job("bs-download", None, {"ids": ["3a1f4"]})
        api.jobs.start()
        row = api.jobs.wait(holder["id"])
    assert row["status"] == "cancelled" and row["result"] is None
    assert sorted(p.name for p in svc.levels.iterdir()) == before
    assert not (svc.data / "bs-tmp").exists()
    assert not [r for r in up.requests if r.url.host.startswith("r2cdn")]


def test_checkpoint_without_progress_is_a_noop():
    checkpoint(None)
    checkpoint(None, "text")
    checkpoint(lambda text: None)  # a plain callable has no check()


@given(st.text(max_size=20))
def test_checkpoint_reports_text_else_checks(text):
    class P(list):
        def __call__(self, t):
            self.append(("text", t))

        def check(self):
            self.append("check")

    p = P()
    checkpoint(p, text)
    checkpoint(p)
    assert p == [("text", text), "check"]
