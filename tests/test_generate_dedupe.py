import hashlib
import threading

import pytest
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.api import create_app
from saber_tooth.source import file_source, url_source, youtube_id
from tests.test_service import _make

VID = "rDQGieROK_w"
FORMS = [
    f"https://www.youtube.com/watch?v={VID}",
    f"https://youtu.be/{VID}?si=abc&t=5",
    f"https://www.youtube.com/shorts/{VID}",
    f"https://music.youtube.com/watch?v={VID}&list=RDAMVM{VID}",
    f"https://m.youtube.com/watch?feature=share&v={VID}",
]
MAP = "a" * 12


@pytest.fixture
def svc(tmp_path):
    return _make(tmp_path)


@pytest.fixture
def client(svc):
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        yield c


@pytest.fixture
def gate(svc):
    """run_generate that blocks until released, recording its keyword arguments."""
    event, calls = threading.Event(), []

    def run(source, progress=None, **kw):
        calls.append(kw)
        event.wait(10)
        svc.store.upsert_map(MAP, "Song", "Song", "", "", None)
        return {"map_id": MAP, "folder": "Song"}

    svc.run_generate = run
    svc.run_generate_event = event
    yield calls
    event.set()


def _release(svc):
    svc.run_generate_event.set()


def test_three_forms_of_one_video_make_one_job(client, svc, gate):
    first = client.post("/api/generate", json={"url": FORMS[0]})
    assert first.status_code == 200
    job = first.json()["job"]
    for form in FORMS[1:3]:
        again = client.post("/api/generate", json={"url": form})
        assert again.status_code == 409
        assert again.json() == {"error": "already being imported", "job": job}


def test_a_library_map_with_the_source_is_refused(client, svc, gate):
    job = client.post("/api/generate", json={"url": FORMS[0]}).json()["job"]
    _release(svc)
    client.app.state.api.jobs.wait(job, timeout=20)
    again = client.post("/api/generate", json={"url": FORMS[1]})
    assert again.status_code == 409
    assert again.json() == {"error": "already imported", "map_id": MAP}
    assert svc.store.find_source(f"yt:{VID}")["id"] == MAP


def test_a_deleted_map_can_be_imported_again(client, svc, gate):
    job = client.post("/api/generate", json={"url": FORMS[0]}).json()["job"]
    _release(svc)
    client.app.state.api.jobs.wait(job, timeout=20)
    svc.store.delete_map(MAP)
    assert client.post("/api/generate", json={"url": FORMS[0]}).status_code == 200


def test_the_title_comes_from_the_lookup_and_names_the_map(client, svc, gate, monkeypatch):
    monkeypatch.setattr(
        "saber_tooth.api.generate_api.video_title", lambda url: "Artist - Song (Official)"
    )
    job = client.post("/api/generate", json={"url": FORMS[0]}).json()["job"]
    assert client.get(f"/api/jobs/{job}").json()["title"] == "Artist - Song (Official)"
    listed = client.get("/api/jobs").json()
    assert [j["title"] for j in listed["running"] + listed["queued"]] == [
        "Artist - Song (Official)"
    ]
    for _ in range(500):
        if gate:
            break
        threading.Event().wait(0.01)
    assert gate == [{"title": "Artist - Song (Official)"}]


def test_without_a_title_the_job_keeps_its_generic_name(client, svc, gate):
    job = client.post("/api/generate", json={"url": FORMS[0]}).json()["job"]
    assert client.get(f"/api/jobs/{job}").json()["title"] == "Generate from YouTube"


def test_a_finished_generate_job_shows_the_created_maps_title(client, svc, gate):
    job = client.post("/api/generate", json={"url": FORMS[0]}).json()["job"]
    _release(svc)
    client.app.state.api.jobs.wait(job, timeout=20)
    listed = {j["id"]: j for j in client.get("/api/jobs").json()["recent"]}
    assert listed[job]["title"] == "Song" and listed[job]["map_id"] == MAP
    assert client.get(f"/api/jobs/{job}").json()["title"] == "Song"


def test_uploads_are_matched_by_content(client, svc, gate):
    same = {"file": ("one.mp3", b"abc", "audio/mpeg")}
    job = client.post("/api/generate", files=same).json()["job"]
    again = client.post("/api/generate", files={"file": ("two.mp3", b"abc", "audio/mpeg")})
    assert again.status_code == 409 and again.json()["job"] == job
    other = client.post("/api/generate", files={"file": ("one.mp3", b"abd", "audio/mpeg")})
    assert other.status_code == 200
    assert not list((svc.data / "uploads").glob("*/two.mp3"))


def test_maps_made_before_sources_get_theirs_from_the_job_args(client, svc):
    svc.store.upsert_map(MAP, "Song", "Song", "", "", None)
    old = svc.store.create_job("generate", None, {"url": FORMS[2]})
    svc.store.update_job(old, "done", result={"map_id": MAP, "folder": "Song"})
    again = client.post("/api/generate", json={"url": FORMS[0]})
    assert again.status_code == 409 and again.json()["map_id"] == MAP


def test_file_source_is_the_sha256(tmp_path):
    path = tmp_path / "a.mp3"
    path.write_bytes(b"hello")
    assert file_source(path) == "sha256:" + hashlib.sha256(b"hello").hexdigest()


@given(
    st.from_regex(r"[A-Za-z0-9_-]{11}", fullmatch=True),
    st.sampled_from(
        [
            "https://www.youtube.com/watch?v={}",
            "https://youtu.be/{}",
            "http://youtu.be/{}?t=3",
            "https://www.youtube.com/shorts/{}",
            "https://music.youtube.com/watch?v={}&list=x",
            "https://www.youtube.com/watch?list=x&v={}&t=9",
        ]
    ),
)
def test_every_form_normalises_to_the_video_id(vid, form):
    assert youtube_id(form.format(vid)) == vid
    assert url_source(form.format(vid)) == f"yt:{vid}"


@given(st.text(max_size=80))
def test_youtube_id_never_raises(text):
    assert youtube_id(text) is None or isinstance(youtube_id(text), str)
