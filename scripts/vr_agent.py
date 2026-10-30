"""Host helper: report the running VR runtime on 127.0.0.1:8101 for the saber-tooth backend.

Runs on the host, outside Docker, with the standard library only; the optional pyopenvr package
(`uv run --with openvr python scripts/vr_agent.py`) adds whether the headset is worn. GET /status
answers {"os", "runtime", "runtimes", "xr_runtime", "worn"}. The backend reads it at VR_AGENT_URL.

Usage: uv run python scripts/vr_agent.py [--port N] [--bind HOST]
"""

import argparse
import contextlib
import json
import sys
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from saber_tooth.vr.model import none_status, status_dict
from saber_tooth.vr.probe import Readers, probe
from saber_tooth.vr.readers import default_readers, detect_os
from saber_tooth.vr.worn import WornMonitor, load_openvr, stderr_log

DEFAULT_PORT = 8101
DEFAULT_BIND = "127.0.0.1"
SAMPLE_S = 2.0
LOG_EVERY_S = 60.0
STOP_JOIN_S = 5.0


def build_status(os_name: str, readers: Readers, monitor: WornMonitor) -> dict:
    found = probe(os_name, readers)
    worn = monitor.read("SteamVR" in found.runtimes)
    return status_dict(os_name, found, worn)


class Sampler:
    """Probes on a timer so a request is answered from memory, never from a slow probe."""

    def __init__(
        self,
        sample: Callable[[], dict],
        fallback: dict,
        interval: float = SAMPLE_S,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._sample = sample
        self._interval = interval
        self._clock = clock
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._logged: dict[str, float] = {}
        self._value = fallback
        self.refresh()

    def latest(self) -> dict:
        return self._value

    def refresh(self) -> None:
        try:
            self._value = self._sample()
        except Exception as exc:
            kind, now = type(exc).__name__, self._clock()
            last = self._logged.get(kind)
            if last is None or now - last >= LOG_EVERY_S:
                self._logged[kind] = now
                print(f"vr_agent: probe failed ({exc}); keeping the last answer", file=sys.stderr)

    def run(self) -> None:
        while not self._stop.wait(self._interval):
            self.refresh()

    def start(self) -> None:
        self._thread = threading.Thread(target=self.run, name="vr-sampler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Ends the loop and waits (bounded) for a refresh already running."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=STOP_JOIN_S)


MAX_DRAIN = 1 << 20  # bytes of a request body read and dropped before an early reply


def make_handler(latest: Callable[[], dict]) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.split("?", 1)[0] == "/status":
                self._send(200, latest())
            else:
                self._send(404, {"error": "not found"})

        def _other(self) -> None:
            self._send(405, {"error": "method not allowed"}, allow=True)

        do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_HEAD = _other

        def _drain(self) -> None:
            """Read and drop the request body: closing with unread data resets the connection."""
            try:
                left = min(int(self.headers.get("Content-Length") or 0), MAX_DRAIN)
            except ValueError:
                left = 0
            while left > 0:
                chunk = self.rfile.read(min(left, 65536))
                if not chunk:
                    break
                left -= len(chunk)

        def _send(self, code: int, body: dict, allow: bool = False) -> None:
            self._drain()
            data = json.dumps(body).encode("utf-8")
            self.send_response(code)
            if allow:
                self.send_header("Allow", "GET")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        def log_message(self, format, *args):
            return  # no per-request access lines

    return Handler


class Server(ThreadingHTTPServer):
    # Reuse would let a second helper bind a taken port on Windows instead of failing.
    allow_reuse_address = False
    daemon_threads = True


def make_server(bind: str, port: int, latest: Callable[[], dict]) -> Server:
    return Server((bind, port), make_handler(latest))


def port_message(bind: str, port: int, exc: OSError) -> str:
    return (
        f"vr_agent: cannot listen on {bind}:{port} ({exc}). Another program uses that port. "
        "Choose a free one with --port N and set "
        "VR_AGENT_URL=http://host.docker.internal:N/status for the backend."
    )


def main(
    argv: list[str] | None = None,
    readers: Readers | None = None,
    monitor: WornMonitor | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="port (default 8101)")
    parser.add_argument("--bind", default=DEFAULT_BIND, help="address (default 127.0.0.1)")
    args = parser.parse_args(argv)
    os_name = detect_os()
    readers = readers or default_readers(os_name)
    monitor = monitor or WornMonitor(load_openvr, stderr_log)
    sampler = Sampler(
        lambda: build_status(os_name, readers, monitor), fallback=none_status(os_name)
    )
    try:
        try:
            server = make_server(args.bind, args.port, sampler.latest)
        except OSError as exc:
            print(port_message(args.bind, args.port, exc), file=sys.stderr)
            return 1
        sampler.start()
        print(
            f"vr_agent: serving http://{args.bind}:{args.port}/status (os={os_name}); Ctrl+C stops"
        )
        try:
            with contextlib.suppress(KeyboardInterrupt):
                server.serve_forever()
        finally:
            sampler.stop()
            server.server_close()
        return 0
    finally:
        monitor.read(False)  # close the background OpenVR session on every exit


if __name__ == "__main__":
    sys.exit(main())
