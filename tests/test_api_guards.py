# ruff: noqa: F811
import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.api.hosts import host_allowed
from saber_tooth.fixer import Flip
from saber_tooth.model import Cut
from saber_tooth.service import map_id_for
from tests.test_api import MID, svc  # noqa: F401
from tests.test_service import NAME, NOTE, _propose

ALLOWED = ["127.0.0.1", "localhost", "127.0.0.1:8100", "localhost:1", "[::1]", "[::1]:8100"]


@pytest.mark.parametrize("host", ALLOWED)
def test_loopback_hosts_are_served(svc, host):
    with TestClient(create_app(svc), base_url=f"http://{host}") as c:
        assert c.get("/api/maps").status_code == 200


@pytest.mark.parametrize("host", ["evil.example", "evil.example:8100", "127.0.0.1.evil.example"])
def test_rebinding_host_is_refused_even_with_matching_origin(svc, host):
    with TestClient(create_app(svc), base_url=f"http://{host}") as c:
        assert c.get("/api/maps").status_code == 403
        resp = c.post("/api/lightshow/learn", headers={"origin": f"http://{host}"})
        assert resp.status_code == 403 and "error" in resp.json()


def test_allowed_hosts_env_extends_the_allowlist(svc, monkeypatch):
    monkeypatch.setenv("SABER_ALLOWED_HOSTS", "saber.lan, Other.Example")
    with TestClient(create_app(svc), base_url="http://saber.lan:8100") as c:
        assert c.get("/api/maps").status_code == 200
    with TestClient(create_app(svc), base_url="http://other.example") as c:
        assert c.get("/api/maps").status_code == 200
    with TestClient(create_app(svc), base_url="http://evil.example") as c:
        assert c.get("/api/maps").status_code == 403


def test_missing_or_empty_host_is_refused():
    allowed = frozenset({"localhost"})
    assert not host_allowed(None, allowed) and not host_allowed("", allowed)


def test_status_change_loses_the_race_against_apply(svc, monkeypatch):
    pid = _propose(svc, map_id_for(NAME), [Flip("Hard", NOTE, Cut(0))])
    stale = svc.store.proposal(pid)  # what set_status read before the apply committed
    svc.apply(map_id_for(NAME))
    monkeypatch.setattr(svc.store, "proposal", lambda _pid: stale)
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        for verb in ("approve", "reject"):
            resp = c.post(f"/api/proposals/{pid}/{verb}")
            assert resp.status_code == 409 and resp.json() == {"error": "proposal already applied"}
    assert svc.store.proposals(MID)[0]["status"] == "applied"
