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


FWD = {"x-forwarded-host": "saber.lan", "x-forwarded-proto": "https"}
PROXY = ("10.0.0.5", 5000)


def _client(svc, base, peer=PROXY):
    return TestClient(create_app(svc), base_url=base, client=peer)


def test_forwarded_headers_are_ignored_when_no_proxy_is_configured(svc, monkeypatch):
    monkeypatch.setenv("SABER_ALLOWED_HOSTS", "saber.lan")
    with _client(svc, "http://evil.example") as c:
        assert c.get("/api/maps", headers=FWD).status_code == 403
    with _client(svc, "http://localhost") as c:
        spoof = {"origin": "https://saber.lan", **FWD}
        assert c.post("/api/lightshow/learn", headers=spoof).status_code == 403


def test_trusted_peer_takes_host_and_scheme_from_forwarded_headers(svc, monkeypatch):
    monkeypatch.setenv("SABER_ALLOWED_HOSTS", "saber.lan, backend")
    monkeypatch.setenv("SABER_TRUSTED_PROXY_IPS", "192.168.0.1, 10.0.0.5/32")
    with _client(svc, "http://backend:8100") as c:
        assert c.get("/api/maps", headers=FWD).status_code == 200
        same = {"origin": "https://saber.lan", **FWD}
        assert c.post("/api/lightshow/learn", headers=same).status_code != 403
        other = {"origin": "http://saber.lan", **FWD}
        assert c.post("/api/lightshow/learn", headers=other).status_code == 403


def test_untrusted_peer_cannot_spoof_forwarded_headers(svc, monkeypatch):
    monkeypatch.setenv("SABER_TRUSTED_PROXY_IPS", "10.0.0.5")
    spoof = {"x-forwarded-host": "localhost"}
    for peer in (("203.0.113.9", 1), ("::1", 1), ("testclient", 1)):
        with _client(svc, "http://evil.example", peer) as c:
            assert c.get("/api/maps", headers=spoof).status_code == 403


def test_trusted_proxy_uses_the_rightmost_forwarded_value(svc, monkeypatch):
    monkeypatch.setenv("SABER_ALLOWED_HOSTS", "saber.lan, backend")
    monkeypatch.setenv("SABER_TRUSTED_PROXY_IPS", "10.0.0.5")
    with _client(svc, "http://backend") as c:
        forged = {"x-forwarded-host": "localhost, evil.example"}
        assert c.get("/api/maps", headers=forged).status_code == 403
        real = {"x-forwarded-host": "evil.example, saber.lan"}
        assert c.get("/api/maps", headers=real).status_code == 200


def test_trusted_peer_without_forwarded_headers_uses_the_request(svc, monkeypatch):
    monkeypatch.setenv("SABER_TRUSTED_PROXY_IPS", "10.0.0.5")
    with _client(svc, "http://localhost") as c:
        assert c.get("/api/maps").status_code == 200


def test_trusted_peer_needs_an_allowed_direct_host(svc, monkeypatch):
    monkeypatch.setenv("SABER_ALLOWED_HOSTS", "saber.lan")
    monkeypatch.setenv("SABER_TRUSTED_PROXY_IPS", "10.0.0.5")
    with _client(svc, "http://backend") as c:
        assert c.get("/api/maps", headers=FWD).status_code == 403
    with _client(svc, "http://localhost") as c:
        assert c.get("/api/maps", headers=FWD).status_code == 200
        bad = {"x-forwarded-host": "evil.example"}
        assert c.get("/api/maps", headers=bad).status_code == 403


@pytest.mark.parametrize("entry", ["10.0.0.0/24", "10.0.0.0/8", "::/0", "fd00::/64"])
def test_proxy_networks_are_refused_at_startup(svc, monkeypatch, entry):
    monkeypatch.setenv("SABER_TRUSTED_PROXY_IPS", f"10.0.0.5, {entry}")
    with pytest.raises(ValueError, match="single proxy addresses"):
        create_app(svc)


def test_proxy_single_addresses_are_accepted(svc, monkeypatch):
    monkeypatch.setenv("SABER_TRUSTED_PROXY_IPS", "10.0.0.5/32, ::1, fd00::2/128")
    create_app(svc)


def test_invalid_proxy_list_fails_loudly(svc, monkeypatch):
    monkeypatch.setenv("SABER_TRUSTED_PROXY_IPS", "not-an-ip")
    with pytest.raises(ValueError):
        create_app(svc)


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
