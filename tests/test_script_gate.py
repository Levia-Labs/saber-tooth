"""Unit tests for scripts/gate.py with a fake runner; no gate is executed."""

from hypothesis import given
from hypothesis import strategies as st

from tests.script_loader import load

gate = load("gate")


def test_select_default_order_and_deep():
    names = gate.select([], [], deep=False, has_frontend=False)
    assert names[0] == "pytest"
    assert "quality:deep" not in names and not any(n.startswith("frontend") for n in names)
    assert gate.select([], [], deep=True, has_frontend=False)[-1] == "quality:deep"


def test_select_frontend_only_when_present():
    assert "frontend:build" in gate.select([], [], has_frontend=True)
    assert "frontend:build" not in gate.select([], [], has_frontend=False)


def test_select_only_and_skip():
    assert gate.select(["quality:gate", "pytest"], []) == ["pytest", "quality:gate"]
    assert "pytest" not in gate.select([], ["pytest"])


def test_excerpt_first_error_line_else_tail():
    log = "ok\nstep\nERROR: boom\nmore\nlast\nend\n"
    assert gate.excerpt(log) == ["ERROR: boom", "more", "last"]
    assert gate.excerpt("a\nb\nc\nd\n") == ["b", "c", "d"]
    assert gate.excerpt("") == []


@given(st.text(max_size=300))
def test_excerpt_never_exceeds_three_lines(text):
    assert len(gate.excerpt(text)) <= 3


def test_log_path_has_no_colon():
    assert gate.log_path("lint:python:check").name == "lint-python-check.log"


def test_run_all_reports_pass_and_fail(tmp_path):
    logs = {}
    for name, text in (("pytest", ""), ("quality:gate", "x\nFAILED y\n")):
        logs[name] = tmp_path / (name.replace(":", "-") + ".log")
        logs[name].write_text(text, encoding="utf-8")
    rc = {"pytest": 0, "quality:gate": 1}
    out: list[str] = []
    code = gate.run_all(["pytest", "quality:gate"], lambda n: (rc[n], 1.2, logs[n]), out.append)
    assert code == 1
    assert out[0] == "pytest rc=0 (1s)"
    assert out[1] == "quality:gate rc=1 (1s)"
    assert f"  log: {logs['quality:gate']}" in out
    assert "  FAILED y" in out
    assert out[-1] == "gate: FAIL (1 failed)"


def test_run_all_pass():
    out: list[str] = []
    assert gate.run_all(["pytest"], lambda n: (0, 0.0, None), out.append) == 0
    assert out[-1] == "gate: PASS (0 failed)"


def test_main_rejects_unknown_gate(capsys):
    assert gate.main(["--only", "nope"]) == 2
    assert "unknown gate" in capsys.readouterr().err
