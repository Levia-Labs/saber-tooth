"""Tests for scripts/crepidoma_bump.py in a temporary repository with a local submodule."""

import subprocess

import pytest

from tests.script_loader import load

bump = load("crepidoma_bump")


def _git(cwd, *args):
    cmd = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "protocol.file.allow=always"]
    return subprocess.run([*cmd, *args], cwd=cwd, check=True, capture_output=True, text=True)


def _commit(path, name):
    (path / name).write_text(name, encoding="utf-8")
    _git(path, "add", ".")
    _git(path, "commit", "-q", "-m", f"add {name}")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q", "-b", "main")
    _commit(origin, "one")
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "submodule", "add", "-q", str(origin), ".crepidoma")
    _git(root, "commit", "-q", "-m", "base")
    _commit(origin, "two")
    monkeypatch.chdir(root)
    return root


def test_rejects_bad_ref(capsys):
    assert bump.bump("--evil") == 2
    assert "invalid ref" in capsys.readouterr().err


def test_log_lines_no_change():
    assert bump.log_lines("a", "a") == ["no change"]


def test_bump_logs_runs_gate_and_stages(repo, monkeypatch, capsys):
    calls = []

    def fake_run(argv, **kw):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0)

    real = subprocess.run
    monkeypatch.setattr(
        bump.subprocess,
        "run",
        lambda argv, **kw: (
            fake_run(argv, **kw) if "gate.py" in " ".join(map(str, argv)) else real(argv, **kw)
        ),
    )
    assert bump.bump("origin/main") == 0
    out = capsys.readouterr().out
    assert "add two" in out and "staged .crepidoma" in out
    assert any(bump.GATES in a for a in calls[0])
    assert ".crepidoma" in _git(repo, "diff", "--cached", "--name-only").stdout


def test_failed_gate_leaves_gitlink_unstaged(repo, monkeypatch, capsys):
    real = subprocess.run
    monkeypatch.setattr(
        bump.subprocess,
        "run",
        lambda argv, **kw: (
            subprocess.CompletedProcess(argv, 1)
            if "gate.py" in " ".join(map(str, argv))
            else real(argv, **kw)
        ),
    )
    assert bump.bump("origin/main") == 1
    assert "not staged" in capsys.readouterr().err
    assert _git(repo, "diff", "--cached", "--name-only").stdout.strip() == ""
