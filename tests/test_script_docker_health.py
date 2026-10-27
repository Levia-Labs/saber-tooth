"""Tests for scripts/docker_health.py with a fake docker runner."""

import json

from tests.script_loader import load

dh = load("docker_health")

PS = "\n".join(
    [
        json.dumps({"Service": "saber-tooth", "State": "running", "Health": "", "ID": "a"}),
        json.dumps({"Service": "analyser", "State": "running", "Health": "unhealthy", "ID": "b"}),
    ]
)
INSPECT = json.dumps([{"State": {"Health": {"Log": [{"Output": "probe failed\n"}]}}}])


def test_parse_ps_lines_and_array():
    assert len(dh.parse_ps(PS)) == 2
    assert dh.parse_ps(json.dumps([{"Service": "x"}])) == [{"Service": "x"}]
    assert dh.parse_ps("  ") == []


def test_is_bad():
    assert dh.is_bad({"State": "exited"})
    assert dh.is_bad({"State": "running", "Health": "unhealthy"})
    assert not dh.is_bad({"State": "running", "Health": "healthy"})


def test_probe_output_tolerates_garbage():
    assert dh.probe_output(INSPECT) == ["probe failed"]
    assert dh.probe_output("not json") == []
    assert dh.probe_output(None) == []


def test_report_unhealthy_shows_probe_and_logs():
    def run(*args):
        if args[0] == "inspect":
            return INSPECT
        if args[1] == "logs":
            return "l1\nl2\n"
        return PS

    lines, rc = dh.report(run)
    assert rc == 1
    assert "saber-tooth state=running health=n/a" in lines
    assert "analyser state=running health=unhealthy" in lines
    assert "  probe: probe failed" in lines and "  log: l2" in lines
    assert lines.count("  probe: probe failed") == 1


def test_report_all_healthy():
    ok = json.dumps({"Service": "s", "State": "running", "Health": "healthy"})
    assert dh.report(lambda *a: ok) == (["s state=running health=healthy"], 0)


def test_report_docker_down():
    lines, rc = dh.report(lambda *a: None)
    assert rc == 1 and "failed" in lines[0]


def test_report_waits_while_starting():
    starting = json.dumps({"Service": "s", "State": "running", "Health": "starting"})
    healthy = json.dumps({"Service": "s", "State": "running", "Health": "healthy"})
    outs = iter([starting, starting, healthy])
    sleeps = []
    lines, rc = dh.report(lambda *a: next(outs), wait=100, sleep=sleeps.append)
    assert rc == 0 and lines == ["s state=running health=healthy"] and len(sleeps) == 2


def test_report_starting_after_wait_is_not_ready():
    starting = json.dumps({"Service": "s", "State": "running", "Health": "starting"})
    lines, rc = dh.report(lambda *a: starting, wait=0, sleep=lambda s: None)
    assert rc == 1 and any("not ready" in ln for ln in lines)
