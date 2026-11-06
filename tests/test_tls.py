import datetime as dt
import ipaddress
import os

import pytest
from cryptography import x509
from hypothesis import given
from hypothesis import strategies as st

from saber_tooth import serve, tls

_label = st.from_regex(r"[a-z0-9]([a-z0-9-]{0,10}[a-z0-9])?", fullmatch=True)
_names = st.lists(_label, min_size=1, max_size=3).map(".".join)
_hosts = st.one_of(_names, st.ip_addresses().map(str))


@given(st.lists(_hosts, max_size=5))
def test_parse_hosts_accepts_valid_and_keeps_defaults(extras):
    out = tls.parse_hosts(",".join(extras))
    assert out[:3] == list(tls.DEFAULT_HOSTS)
    assert len(out) == len(set(out))
    for host in out:
        assert tls.parse_host(host) == host


@given(st.text())
def test_parse_host_output_is_ip_or_valid_name(raw):
    try:
        host = tls.parse_host(raw)
    except ValueError:
        return
    try:
        ipaddress.ip_address(host)
    except ValueError:
        assert host == host.lower() and " " not in host and "*" not in host and "/" not in host


@pytest.mark.parametrize("bad", ["a b", "*.lan", "exa_mple.com", "-a.com", "a/b", "http://x", ""])
def test_parse_host_rejects(bad):
    with pytest.raises(ValueError):
        tls.parse_host(bad)


def test_parse_hosts_rejects_bad_extra():
    with pytest.raises(ValueError):
        tls.parse_hosts("saber.lan,$(rm)")


def _sans(path):
    cert = x509.load_pem_x509_certificate(path.read_bytes())
    return cert, tls._cert_names(cert)


def test_generate_sans_validity_and_perms(tmp_path):
    cert_path, key_path = tls.ensure_cert(tmp_path, "Saber.LAN, 192.168.1.5")
    cert, names = _sans(cert_path)
    assert names == {"localhost", "127.0.0.1", "::1", "saber.lan", "192.168.1.5"}
    assert cert.not_valid_after_utc - cert.not_valid_before_utc <= dt.timedelta(days=826)
    if os.name == "posix":
        assert key_path.stat().st_mode & 0o777 == 0o600


def test_reuse_and_regenerate_on_san_change(tmp_path):
    cert_path, _ = tls.ensure_cert(tmp_path, None)
    first = cert_path.read_bytes()
    tls.ensure_cert(tmp_path, None)
    assert cert_path.read_bytes() == first
    tls.ensure_cert(tmp_path, "saber.lan")
    assert "saber.lan" in _sans(cert_path)[1]


def test_regenerate_when_expiring_or_key_missing(tmp_path):
    cert_path, key_path = tls.ensure_cert(tmp_path, None)
    first = cert_path.read_bytes()
    late = dt.datetime.now(dt.UTC) + dt.timedelta(days=tls.VALID_DAYS - 10)
    tls.ensure_cert(tmp_path, None, now=late)
    assert cert_path.read_bytes() != first
    second = cert_path.read_bytes()
    key_path.unlink()
    tls.ensure_cert(tmp_path, None, now=late)
    assert key_path.is_file() and cert_path.read_bytes() != second


def test_regenerate_on_corrupt_cert(tmp_path):
    cert_path, _ = tls.ensure_cert(tmp_path, None)
    cert_path.write_text("junk", encoding="utf-8")
    tls.ensure_cert(tmp_path, None)
    assert _sans(cert_path)[1]


def test_resolve_off_by_default_and_toggles(tmp_path):
    assert tls.resolve({}) is None
    assert tls.resolve({"SABER_TLS": "0"}) is None
    for on in ("1", "true", "TRUE"):
        cert, key = tls.resolve({"SABER_TLS": on, "DATA_DIR": str(tmp_path)})
        assert cert.parent == tmp_path / "tls" and key.is_file()


def test_resolve_user_pair_never_overwritten(tmp_path):
    cert, key = tls.ensure_cert(tmp_path / "gen", None)
    before = (cert.read_bytes(), key.read_bytes())
    env = {"SABER_TLS": "1", "SABER_TLS_CERT": str(cert), "SABER_TLS_KEY": str(key)}
    assert tls.resolve(env) == (cert, key)
    assert (cert.read_bytes(), key.read_bytes()) == before
    with pytest.raises(ValueError):
        tls.resolve({"SABER_TLS": "1", "SABER_TLS_CERT": str(cert)})
    with pytest.raises(ValueError):
        tls.resolve({**env, "SABER_TLS_KEY": str(tmp_path / "missing")})


def test_resolve_rejects_unusable_user_pair(tmp_path):
    cert, key = tls.ensure_cert(tmp_path / "a", None)
    _, other_key = tls.ensure_cert(tmp_path / "b", None)
    env = {"SABER_TLS": "1", "SABER_TLS_CERT": str(cert), "SABER_TLS_KEY": str(other_key)}
    with pytest.raises(ValueError, match="usable pair"):
        tls.resolve(env)
    junk = tmp_path / "junk.pem"
    junk.write_text("junk", encoding="utf-8")
    with pytest.raises(ValueError, match="usable pair"):
        tls.resolve({**env, "SABER_TLS_KEY": str(key), "SABER_TLS_CERT": str(junk)})


def test_regenerate_on_mismatched_pair(tmp_path):
    cert_path, key_path = tls.ensure_cert(tmp_path / "a", None)
    _, other_key = tls.ensure_cert(tmp_path / "b", None)
    key_path.write_bytes(other_key.read_bytes())
    tls.ensure_cert(tmp_path / "a", None)
    assert tls.resolve({"SABER_TLS": "1", "DATA_DIR": str(tmp_path / "a")}) == (
        cert_path,
        key_path,
    )
    tls.resolve(
        {"SABER_TLS": "1", "SABER_TLS_CERT": str(cert_path), "SABER_TLS_KEY": str(key_path)}
    )


def test_regenerate_on_unreadable_key(tmp_path, monkeypatch):
    cert_path, key_path = tls.ensure_cert(tmp_path, None)
    first = cert_path.read_bytes()
    monkeypatch.setattr(tls.os, "access", lambda *a, **k: False)
    assert not tls._current(cert_path, key_path, tls.parse_hosts(None), dt.datetime.now(dt.UTC))
    tls.ensure_cert(tmp_path, None)
    assert cert_path.read_bytes() != first


def test_no_temp_files_left(tmp_path):
    cert_path, _ = tls.ensure_cert(tmp_path, None)
    assert sorted(p.name for p in cert_path.parent.iterdir()) == ["cert.pem", "key.pem"]


@given(st.text())
def test_parse_host_rejects_percent(raw):
    with pytest.raises(ValueError):
        tls.parse_host(raw + "%eth0")


def test_client_verify_warns_for_remote_only(capsys):
    off = {"SABER_TLS_VERIFY": "0"}
    assert tls.client_verify("https://127.0.0.1:8100", off) is False
    assert tls.client_verify("https://localhost:8100", off) is False
    assert capsys.readouterr().err == ""
    assert tls.client_verify("https://saber.lan:8100", off) is False
    assert "warning" in capsys.readouterr().err
    assert tls.client_verify("https://saber.lan:8100", {}) is True
    assert capsys.readouterr().err == ""


def test_verify_enabled():
    assert tls.verify_enabled({}) is True
    assert tls.verify_enabled({"SABER_TLS_VERIFY": "0"}) is False
    assert tls.verify_enabled({"SABER_TLS_VERIFY": "1"}) is True


def test_serve_rejects_bad_config(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("SABER_TLS", "1")
    monkeypatch.setenv("SABER_TLS_CERT", str(tmp_path / "nope"))
    monkeypatch.setenv("SABER_TLS_KEY", str(tmp_path / "nope"))
    assert serve.main([]) == 64
    assert "error" in capsys.readouterr().err


def test_serve_passes_ssl_files(monkeypatch, tmp_path):
    seen = {}
    monkeypatch.setattr(serve.uvicorn, "run", lambda app, **kw: seen.update(kw))
    monkeypatch.setenv("SABER_TLS", "1")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert serve.main([]) == 0
    assert seen["ssl_certfile"].endswith("cert.pem") and seen["ssl_keyfile"].endswith("key.pem")
    monkeypatch.delenv("SABER_TLS")
    seen.clear()
    serve.main([])
    assert "ssl_certfile" not in seen


def test_health_follows_scheme(monkeypatch):
    calls = []

    class Opener:
        def __init__(self, handlers):
            self.handlers = handlers

        def open(self, url, **kw):
            calls.append((url, self.handlers))

    monkeypatch.setattr(serve.urllib.request, "build_opener", lambda *h: Opener(h))
    assert serve.health({"SABER_TLS": "1"}) == 0
    assert serve.health({}) == 0
    url, handlers = calls[0]
    assert url.startswith("https://127.0.0.1:")
    assert any(isinstance(h, serve.urllib.request.HTTPSHandler) for h in handlers)
    assert any(isinstance(h, serve.urllib.request.ProxyHandler) for h in handlers)
    url, handlers = calls[1]
    assert url.startswith("http://127.0.0.1:")
    assert not any(isinstance(h, serve.urllib.request.HTTPSHandler) for h in handlers)
