"""Container launcher: `python -m saber_tooth.serve` runs uvicorn, over HTTPS when SABER_TLS is on.

`python -m saber_tooth.serve --health` is the container HEALTHCHECK probe; it follows the scheme
and, for the self-signed certificate, skips verification against 127.0.0.1 only.
"""

import os
import ssl
import sys
import urllib.request

import uvicorn

from saber_tooth import tls

PORT = 8100


def health(env: dict[str, str] | None = None) -> int:
    env = dict(os.environ) if env is None else env
    on = tls.tls_enabled(env)
    url = f"{'https' if on else 'http'}://127.0.0.1:{PORT}/api/health"
    handlers: list[urllib.request.BaseHandler] = [urllib.request.ProxyHandler({})]
    if on:  # loopback self-signed certificate: nothing to verify against
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        handlers.append(urllib.request.HTTPSHandler(context=ctx))
    try:
        urllib.request.build_opener(*handlers).open(url, timeout=3)
    except OSError:
        return 1
    return 0


def main(argv: list[str]) -> int:
    if "--health" in argv:
        return health()
    try:
        pair = tls.resolve(os.environ)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 64
    kwargs = {"ssl_certfile": str(pair[0]), "ssl_keyfile": str(pair[1])} if pair else {}
    uvicorn.run("saber_tooth.api:app", host="0.0.0.0", port=PORT, **kwargs)  # noqa: S104
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
