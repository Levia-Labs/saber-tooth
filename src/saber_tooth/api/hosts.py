"""Host header allowlist: the guard against DNS rebinding."""

import os

LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "[::1]"})
ENV_VAR = "SABER_ALLOWED_HOSTS"


def _hostname(header: str) -> str:
    """The host part of a Host header, port removed, lowercased; IPv6 keeps its brackets."""
    host = header.strip().lower()
    if host.startswith("["):
        return host[: host.find("]") + 1] if "]" in host else host
    return host.rsplit(":", 1)[0] if ":" in host else host


def allowed_hosts() -> frozenset[str]:
    """Loopback names plus the comma-separated names in SABER_ALLOWED_HOSTS."""
    extra = {_hostname(h) for h in os.environ.get(ENV_VAR, "").split(",") if h.strip()}
    return LOCAL_HOSTS | extra


def host_allowed(header: str | None, allowed: frozenset[str]) -> bool:
    return bool(header) and _hostname(header or "") in allowed
