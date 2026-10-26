"""Host header allowlist: the guard against DNS rebinding."""

import ipaddress
import os
from collections.abc import Mapping

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


PROXY_VAR = "SABER_TRUSTED_PROXY_IPS"

Network = ipaddress.IPv4Network | ipaddress.IPv6Network


def trusted_proxies() -> tuple[Network, ...]:
    """Networks from the comma list in SABER_TRUSTED_PROXY_IPS; empty means forwarding is off.

    Only single addresses (bare IPs, /32 or /128) are accepted, so a wide network that
    contains clients can never be trusted. Anything else raises ValueError at start-up.
    """
    items = [i.strip() for i in os.environ.get(PROXY_VAR, "").split(",") if i.strip()]
    nets = tuple(ipaddress.ip_network(i, strict=False) for i in items)
    for item, net in zip(items, nets, strict=True):
        if net.num_addresses != 1:
            raise ValueError(f"{PROXY_VAR}: {item!r} is a network; list single proxy addresses")
    return nets


def peer_trusted(peer: str | None, proxies: tuple[Network, ...]) -> bool:
    try:
        addr = ipaddress.ip_address(peer or "")
    except ValueError:
        return False
    return any(addr.version == net.version and addr in net for net in proxies)


def _last(value: str | None) -> str:
    return (value or "").split(",")[-1].strip()


def effective_origin(headers: Mapping[str, str], scheme: str, trusted: bool) -> tuple[str, str]:
    """The (scheme, host header) the client addressed.

    Forwarded headers count only when the peer is a trusted proxy; the rightmost value
    (the one that proxy appended) wins and an absent or empty one falls back to the
    request's own scheme and Host.
    """
    host = headers.get("host", "")
    if trusted:
        host = _last(headers.get("x-forwarded-host")) or host
        scheme = _last(headers.get("x-forwarded-proto")).lower() or scheme
    return scheme, host


def host_allowed(header: str | None, allowed: frozenset[str]) -> bool:
    return bool(header) and _hostname(header or "") in allowed
