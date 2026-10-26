# 0009 Configurable container user and proxy trust

## Context

The container user `app` had a fixed uid 1000. On a Linux host the `/levels` bind mount is owned by the host user, so any other uid could not write the sibling map folders. Separately, behind a TLS proxy the service sees plain `http` and the backend `Host`, so the `Origin` check refused every legitimate browser write. Trusting `X-Forwarded-*` from any client would let a DNS-rebinding page claim `X-Forwarded-Host: localhost` and bypass the host allowlist.

## Decision

1. `docker-entrypoint.sh` starts as root, sets the uid and gid of `app` from `PUID` and `PGID` (default 1000), chowns `/data` and drops privileges with `setpriv` before it executes the server. It never chowns `/levels`; `LEVELS_DIR` must be writable by `PUID`.
2. `SABER_TRUSTED_PROXY_IPS` is a comma list of IPs or CIDRs, empty by default, which means forwarded headers are ignored. When the TCP peer is inside the list, scheme and host for the allowlist and `Origin` checks come from the rightmost value of `X-Forwarded-Proto` and `X-Forwarded-Host`, the one the trusted proxy appended. The host is still checked against the allowlist, including `SABER_ALLOWED_HOSTS`.
3. An invalid entry in the list stops start-up.

## Consequences

1. Linux hosts write maps without `chmod` on user data; Docker Desktop hosts keep the defaults.
2. The container runs a root entrypoint for a moment, but the server never runs as root.
3. A proxy deployment needs the proxy IP or network in `SABER_TRUSTED_PROXY_IPS`, the public name in `SABER_ALLOWED_HOSTS`, and a proxy that appends rather than passes through client-supplied forwarded headers.
4. Any client outside the trusted networks cannot influence the checks through forwarded headers.
