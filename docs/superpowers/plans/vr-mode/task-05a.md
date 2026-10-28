# Task 5: Host helper `scripts/vr_agent.py` and `task st:vr-agent`

The helper runs on the host, outside Docker. It probes in the background every 2 s and answers `GET /status` from the last sample, so a slow `tasklist` never costs the backend its 300 ms budget. It binds `127.0.0.1:8101`; `--port` changes the port and `--bind` the address (Docker on Linux reaches the host through the bridge gateway, not loopback; the docs in Task 19 say when to use it). A taken port ends the run with a message that names `--port` and `VR_AGENT_URL`. The binding disables address reuse: on Windows `SO_REUSEADDR` would let a second helper bind the same port without an error.

**Files:**

- Create: `scripts/vr_agent.py`
- Modify: `tasks/Taskfile.yml` (append one task after `docker-health`)
- Test: `tests/test_script_vr_agent.py`

**Interfaces:**

Consumes: `Readers`, `probe` (`vr/probe.py`), `default_readers`, `detect_os` (`vr/readers.py`), `WornMonitor`, `load_openvr`, `stderr_log` (`vr/worn.py`), `status_dict`, `none_status` (`vr/model.py`).

Produces (`scripts/vr_agent.py`):

1. `DEFAULT_PORT = 8101`, `DEFAULT_BIND = "127.0.0.1"`, `SAMPLE_S = 2.0`.
2. `build_status(os_name: str, readers: Readers, monitor: WornMonitor) -> dict`: one probe plus the worn check, in the documented shape.
3. `Sampler(sample: Callable[[], dict], fallback: dict, interval: float = SAMPLE_S)` with `latest() -> dict`, `refresh() -> None` (keeps the last value when `sample` raises), `run() -> None` (loop until `stop()`), `stop() -> None`. The constructor takes the first sample before returning.
4. `make_handler(latest: Callable[[], dict]) -> type[BaseHTTPRequestHandler]`: `GET /status` answers 200 JSON from `latest()`; any other path 404 `{"error": "not found"}`; no access log.
5. `Server(ThreadingHTTPServer)` with `allow_reuse_address = False`; `make_server(bind: str, port: int, latest) -> Server`.
6. `port_message(bind: str, port: int, exc: OSError) -> str`.
7. `main(argv: list[str] | None = None, readers: Readers | None = None, monitor: WornMonitor | None = None) -> int`: 0 after Ctrl+C, 1 when the port is taken.

The task, in `tasks/Taskfile.yml`:

```yaml
vr-agent:
  desc: "Run the VR runtime helper on the host (port 8101). Usage: task st:vr-agent [-- --port N --bind HOST]"
  cmds: ["uv run python scripts/vr_agent.py {{.CLI_ARGS}}"]
```

- [ ] **Step 1: Write the failing test**

Create `tests/test_script_vr_agent.py`:

```python
"""scripts/vr_agent.py: the status shape, the HTTP answer and the port conflict; no real probes."""

import http.client
import json
import socket
import threading
from pathlib import Path

from saber_tooth.vr.model import none_status
from saber_tooth.vr.probe import Readers
from saber_tooth.vr.worn import WornMonitor
from tests.script_loader import load

agent = load("vr_agent")

KEYS = {"os", "runtime", "runtimes", "xr_runtime", "worn"}


def fake_readers(processes=()):
    return Readers(lambda: list(processes), lambda: [], lambda path: "")


def quiet_monitor():
    return WornMonitor(lambda: None, lambda line: None)


def test_build_status_has_exactly_the_documented_keys():
    status = agent.build_status("windows", fake_readers(["vrserver.exe"]), quiet_monitor())
    assert set(status) == KEYS
    assert status["runtime"] == "SteamVR" and status["runtimes"] == ["SteamVR"]
    assert status["os"] == "windows" and status["worn"] is None


def test_build_status_asks_for_worn_only_while_steamvr_runs():
    asked = []

    class Spy:
        def read(self, steamvr_running):
            asked.append(steamvr_running)
            return True if steamvr_running else None

    on = agent.build_status("windows", fake_readers(["vrserver.exe"]), Spy())
    off = agent.build_status("windows", fake_readers(["OVRServer_x64.exe"]), Spy())
    assert asked == [True, False] and on["worn"] is True and off["worn"] is None


def test_sampler_takes_a_first_sample_and_keeps_the_last_one_on_failure():
    values = iter([{"n": 1}, {"n": 2}])

    def sample():
        try:
            return next(values)
        except StopIteration:
            raise RuntimeError("probe broke") from None

    sampler = agent.Sampler(sample, fallback={"n": 0})
    assert sampler.latest() == {"n": 1}
    sampler.refresh()
    assert sampler.latest() == {"n": 2}
    sampler.refresh()
    assert sampler.latest() == {"n": 2}


def test_sampler_falls_back_when_the_first_sample_fails():
    def sample():
        raise RuntimeError("probe broke")

    assert agent.Sampler(sample, fallback={"n": 0}).latest() == {"n": 0}


def get(port, path):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.request("GET", path)
        res = conn.getresponse()
        return res.status, res.getheader("Content-Type"), json.loads(res.read())
    finally:
        conn.close()


def test_status_endpoint_serves_json_and_other_paths_are_404():
    status = none_status("linux")
    server = agent.make_server("127.0.0.1", 0, lambda: status)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        code, ctype, body = get(port, "/status")
        assert code == 200 and ctype == "application/json" and set(body) == KEYS
        assert body == status
        assert get(port, "/status?x=1")[0] == 200
        assert get(port, "/")[0] == 404 and get(port, "/status/more")[0] == 404
    finally:
        server.shutdown()
        server.server_close()


def test_a_taken_port_ends_with_a_message_naming_the_flag_and_the_variable(capsys):
    taken = socket.socket()
    taken.bind(("127.0.0.1", 0))
    taken.listen()
    try:
        port = taken.getsockname()[1]
        code = agent.main(["--port", str(port)], readers=fake_readers(), monitor=quiet_monitor())
    finally:
        taken.close()
    err = capsys.readouterr().err
    assert code == 1
    assert "--port" in err and "VR_AGENT_URL" in err and str(port) in err


def test_defaults_are_the_spec_values():
    assert agent.DEFAULT_PORT == 8101 and agent.DEFAULT_BIND == "127.0.0.1"
    assert agent.SAMPLE_S == 2.0 and agent.Server.allow_reuse_address is False


def test_the_task_exists_and_runs_the_script():
    text = (Path(__file__).resolve().parents[1] / "tasks" / "Taskfile.yml").read_text(
        encoding="utf-8"
    )
    assert "  vr-agent:" in text and "uv run python scripts/vr_agent.py {{.CLI_ARGS}}" in text
```

- [ ] **Step 2: Run it to see it fail**

Run: `rtk proxy uv run pytest -q tests/test_script_vr_agent.py`
Expected: FAIL: `FileNotFoundError` for `scripts/vr_agent.py` (the loader cannot find the script).

Continued in [task-05b.md](task-05b.md).
