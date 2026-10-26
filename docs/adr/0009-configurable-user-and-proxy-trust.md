# 0009 Configurable container user and proxy trust

## Context

The container user `app` had a fixed uid 1000. On a Linux host the `/levels` bind mount is owned by the host user, so any other uid could not write the sibling map folders. Separately, behind a TLS proxy the service sees plain `http` and the backend `Host`, so the `Origin` check refused every legitimate browser write. Trusting `X-Forwarded-*` from any client would let a DNS-rebinding page claim `X-Forwarded-Host: localhost` and bypass the host allowlist.

## Decision

1. `docker-entrypoint.sh` starts as root, sets the uid and gid of `app` from `PUID` and `PGID` (default 1000), chowns `/data` and drops privileges with `setpriv` before it executes the server. It never chowns `/levels`; `LEVELS_DIR` must be writable by `PUID`.
2. `SABER_TRUSTED_PROXY_IPS` is a comma list of single addresses (bare IPs, `/32` or `/128`), empty by default, which means forwarded headers are ignored. When the TCP peer is in the list, scheme and host for the `Origin` check come from the rightmost value of `X-Forwarded-Proto` and `X-Forwarded-Host`. Both the direct `Host` header and the forwarded host must be in the allowlist (loopback names plus `SABER_ALLOWED_HOSTS`), so a proxy that forgets to overwrite `X-Forwarded-Host` cannot be used to bypass the DNS-rebinding guard.
3. An invalid entry, or any network wider than one address, stops start-up with an error, so client networks cannot be trusted by mistake.

## Consequences

1. Linux hosts write maps without `chmod` on user data; Docker Desktop hosts keep the defaults.
2. The container runs a root entrypoint for a moment, but the server never runs as root.
3. A proxy deployment needs the proxy address in `SABER_TRUSTED_PROXY_IPS`, and both the public name and the proxy upstream host name in `SABER_ALLOWED_HOSTS`. The proxy must overwrite, not append, `X-Forwarded-Host` and `X-Forwarded-Proto`. nginx:

   proxy_set_header Host $host;
   proxy_set_header X-Forwarded-Host $host;
   proxy_set_header X-Forwarded-Proto $scheme;

4. Any client outside the trusted addresses cannot influence the checks through forwarded headers.
