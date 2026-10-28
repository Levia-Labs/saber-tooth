# Task 11: API routes and 422 validation

`api/core.py` is at 287 lines and `api/__init__.py` has another lane's edits, so the logic goes in `api/crop_api.py` (class `CropApi`) and the routes in `api/crop_routes.py`, wired with three anchored edits in `api/__init__.py`.

**Files:**

- Create: `src/saber_tooth/api/crop_api.py`
- Create: `src/saber_tooth/api/crop_routes.py`
- Modify: `src/saber_tooth/api/__init__.py`
- Test: `tests/test_api_crop.py`

**Interfaces:**

Consumes: `Api.map_id(raw) -> str` (404 `MapNotFound` for unknown or malformed ids), `Api.store`, `Api.jobs.submit(kind, fn, *args, map_id=...)`, `Api.service`; `ApiError(status, message)`; `MapUnreadable`; `CropError`; `Service.crop_timeline/crop_check/crop_map` (Task 10).

Produces:

```python
# saber_tooth.api.crop_api
class CropApi:
    def __init__(self, api: Api) -> None
    def timeline(self, raw: str) -> dict                      # 404 unknown map, 409 unreadable, 422 CropError message
    def crop(self, raw: str, start: object, end: object) -> dict   # {"job": id}; 422 on a bad number or broken rule; 409 when the map has a queued or running job

# saber_tooth.api.crop_routes
def register(app: FastAPI, crop: CropApi) -> None
    # GET  /api/maps/{map_id}/timeline
    # POST /api/maps/{map_id}/crop   body {"start_beat": number, "end_beat": number}; 400 on a body that is not JSON
```

The crop job has kind `crop` and `map_id`, so `Store.has_active_job(map_id)` blocks a second job and the delete route's guard (`service/delete.py:30`) blocks deleting the source while it runs.

- [ ] **Step 1: Write the failing test**

Create `tests/test_api_crop.py`:

```python
# ruff: noqa: F811
import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.service import map_id_for
from tests.crop_helpers import NAME, cuts, make_service  # noqa: F401
from tests.test_api import _wait
from tests.test_service import _hashes

MID = map_id_for(NAME)


@pytest.fixture
def http(tmp_path):
    svc = make_service(tmp_path)
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        c.svc = svc
        yield c


def test_timeline_route_returns_the_contract(http):
    body = http.get(f"/api/maps/{MID}/timeline").json()
    assert body["map_id"] == MID and set(body["lengths"]) == {"60", "120"}
    assert body["lengths"]["60"]["suggestions"][0]["end_kind"] in {
        "section",
        "phrase",
        "bar4",
        "bar",
    }
    assert body["map_only"] is True


def test_timeline_for_an_unknown_map_is_404(http):
    assert http.get(f"/api/maps/{'0' * 12}/timeline").status_code == 404
    assert http.get("/api/maps/not-an-id/timeline").status_code == 404


def test_timeline_for_an_unreadable_map_is_409(http):
    http.svc.store.upsert_map("b" * 12, "Broken", "Broken", "", "", "bad json")
    assert http.get(f"/api/maps/{'b' * 12}/timeline").status_code == 409


def test_timeline_without_standard_notes_is_422(http):
    info = http.svc.levels / NAME / "Info.dat"
    info.write_text(
        info.read_text(encoding="utf-8").replace('"Standard"', '"360Degree"'), encoding="utf-8"
    )
    resp = http.get(f"/api/maps/{MID}/timeline")
    assert resp.status_code == 422 and "no Standard difficulty has notes" in resp.json()["error"]


def test_crop_job_writes_a_new_folder(http, cuts):
    original = http.svc.levels / NAME
    before = _hashes(original)
    window = http.get(f"/api/maps/{MID}/timeline").json()["lengths"]["60"]["suggestions"][0]
    body = {"start_beat": window["start_beat"], "end_beat": window["end_beat"]}
    job = _wait(http, http.post(f"/api/maps/{MID}/crop", json=body).json()["job"])
    assert job["status"] == "done" and job["kind"] == "crop"
    assert job["result"]["folder"] == "Song [1 min]"
    assert job["result"]["cropped_id"] == map_id_for("Song [1 min]")
    assert _hashes(original) == before
    folders = {m["folder"] for m in http.get("/api/maps").json()["items"]}
    assert "Song [1 min]" in folders


@pytest.mark.parametrize(
    ("body", "rule"),
    [
        ({"start_beat": "x", "end_beat": 3}, "start_beat must be a number"),
        ({"start_beat": 0, "end_beat": None}, "end_beat must be a number"),
        ({"start_beat": True, "end_beat": 3}, "start_beat must be a number"),
        ({"start_beat": -1, "end_beat": 3}, "start_beat must be a number"),
        ({"start_beat": 8, "end_beat": 8}, "end_beat must be after start_beat"),
        ({"start_beat": 5, "end_beat": 133}, "section boundary"),
        ({"start_beat": 0, "end_beat": 64}, "outside the bands"),
        ({"start_beat": 0, "end_beat": 128.5}, "not an allowed end point"),
        ([], "start_beat must be a number"),
    ],
)
def test_crop_422_names_the_rule(http, body, rule):
    resp = http.post(f"/api/maps/{MID}/crop", json=body)
    assert resp.status_code == 422 and rule in resp.json()["error"]


def test_crop_with_a_body_that_is_not_json_is_400(http):
    resp = http.post(f"/api/maps/{MID}/crop", content=b"nope")
    assert resp.status_code == 400


def test_crop_is_409_while_the_map_has_a_running_job(http):
    http.svc.store.create_job("scan", MID)
    resp = http.post(f"/api/maps/{MID}/crop", json={"start_beat": 0, "end_beat": 128})
    assert resp.status_code == 409


def test_crop_of_an_unknown_map_is_404(http):
    resp = http.post(f"/api/maps/{'0' * 12}/crop", json={"start_beat": 0, "end_beat": 128})
    assert resp.status_code == 404
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest tests/test_api_crop.py -q`
Expected: FAIL: the first test gets 404 or the SPA response for `/timeline` (the route does not exist).

- [ ] **Step 3: Implement**

Create `src/saber_tooth/api/crop_api.py`:

```python
"""Crop highlight API logic: the timeline and the crop job."""

import math

from saber_tooth.api.core import Api, ApiError
from saber_tooth.crop.errors import CropError
from saber_tooth.service import MapUnreadable


def _beat(value: object, name: str) -> float:
    bad = isinstance(value, bool) or not isinstance(value, int | float)
    if bad or not math.isfinite(value) or value < 0:  # type: ignore[operator]
        raise ApiError(422, f"{name} must be a number of beats, 0 or more")
    return float(value)  # type: ignore[arg-type]


class CropApi:
    """Timeline and crop-job calls over one Api, shared by the REST routes and the MCP tools."""

    def __init__(self, api: Api) -> None:
        self.api = api
        self.service = api.service

    def _ready(self, raw: str) -> str:
        map_id = self.api.map_id(raw)
        row = next(m for m in self.api.store.list_maps() if m["id"] == map_id)
        if row["parse_error"]:
            raise MapUnreadable(f"map {row['folder']} cannot be read: {row['parse_error']}")
        return map_id

    def timeline(self, raw: str) -> dict:
        map_id = self._ready(raw)
        try:
            return self.service.crop_timeline(map_id)  # type: ignore[attr-defined]
        except CropError as exc:
            raise ApiError(422, str(exc)) from None

    def crop(self, raw: str, start: object, end: object) -> dict:
        map_id = self._ready(raw)
        start_beat, end_beat = _beat(start, "start_beat"), _beat(end, "end_beat")
        if self.api.store.has_active_job(map_id):
            raise ApiError(409, "the map has a queued or running job")
        try:
            self.service.crop_check(map_id, start_beat, end_beat)  # type: ignore[attr-defined]
        except CropError as exc:
            raise ApiError(422, str(exc)) from None
        run = self.service.crop_map  # type: ignore[attr-defined]
        job = self.api.jobs.submit("crop", run, map_id, start_beat, end_beat, map_id=map_id)
        return {"job": job}
```

Create `src/saber_tooth/api/crop_routes.py`:

```python
"""HTTP routes for the crop highlight; the logic lives in crop_api.py."""

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool

from saber_tooth.api.core import ApiError
from saber_tooth.api.crop_api import CropApi


def register(app: FastAPI, crop: CropApi) -> None:
    @app.get("/api/maps/{map_id}/timeline")
    def timeline(map_id: str):
        return crop.timeline(map_id)

    @app.post("/api/maps/{map_id}/crop")
    async def start_crop(map_id: str, request: Request):
        try:
            body = await request.json()
        except ValueError:
            raise ApiError(400, 'send JSON {"start_beat", "end_beat"}') from None
        fields = body if isinstance(body, dict) else {}
        return await run_in_threadpool(
            crop.crop, map_id, fields.get("start_beat"), fields.get("end_beat")
        )
```

Edit `src/saber_tooth/api/__init__.py` with three anchored edits:

1. After the line `from saber_tooth.api.core import Api, ApiError, _error` add:

```python
from saber_tooth.api.crop_api import CropApi
from saber_tooth.api.crop_routes import register as register_crop
```

2. Insert the line `    crop_api = CropApi(api)` directly above `    mcp_app = build_mcp(api, bs).streamable_http_app(`. Leave the `build_mcp` call as it is; Task 12 adds `crop_api` to it.

3. Replace the line `    register_beatsaver(app, bs)` with:

```python
register_beatsaver(app, bs)
register_crop(app, crop_api)
```

- [ ] **Step 4: Run to pass**

Run: `uv run pytest tests/test_api_crop.py tests/test_api_fix.py tests/test_api.py -q`
Expected: all pass (`test_api_crop.py` has 17 cases with the nine parametrized rule cases).

- [ ] **Step 5: Lint**

Run: `uv run ruff check src/saber_tooth/api tests/test_api_crop.py && uv run ruff format --check src/saber_tooth/api/crop_api.py src/saber_tooth/api/crop_routes.py tests/test_api_crop.py`
Expected: no findings. The `# type: ignore` comments sit on attributes attached at import time; if the repo's checker does not use them, ruff leaves them alone.

- [ ] **Step 6: Commit:** main thread runs `task git:commit -- "feat: crop timeline and crop job routes"` (subagents never commit).

---
