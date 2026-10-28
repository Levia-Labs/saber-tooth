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


class RecordingMonitor:
    def __init__(self):
        self.asked = []

    def read(self, steamvr_running):
        self.asked.append(steamvr_running)
        return None


def test_ctrl_c_closes_the_worn_session_before_exit(monkeypatch):
    class Interrupted:
        def serve_forever(self):
            raise KeyboardInterrupt

        def server_close(self):
            pass

    monkeypatch.setattr(agent, "make_server", lambda bind, port, latest: Interrupted())
    monitor = RecordingMonitor()
    code = agent.main(["--port", "0"], readers=fake_readers(["vrserver.exe"]), monitor=monitor)
    assert code == 0
    assert monitor.asked[-1] is False


def test_a_taken_port_also_closes_the_worn_session(monkeypatch):
    def refuse(bind, port, latest):
        raise OSError("in use")

    monkeypatch.setattr(agent, "make_server", refuse)
    monitor = RecordingMonitor()
    code = agent.main(["--port", "1"], readers=fake_readers(["vrserver.exe"]), monitor=monitor)
    assert code == 1
    assert monitor.asked[-1] is False
