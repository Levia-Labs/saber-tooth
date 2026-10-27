"""Tests for scripts/lane.py against a temporary git repository with a local submodule."""

import subprocess

import pytest

from tests.script_loader import load

lane = load("lane")


def _git(cwd, *args):
    cmd = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "protocol.file.allow=always"]
    subprocess.run([*cmd, *args], cwd=cwd, check=True, capture_output=True)


def _write(path, text):
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    sub = tmp_path / "sub"
    sub.mkdir()
    _git(sub, "init", "-q", "-b", "main")
    _write(sub / "f", "x")
    _git(sub, "add", ".")
    _git(sub, "commit", "-q", "-m", "s")
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "submodule", "add", "-q", str(sub), ".crepidoma")
    _write(root / "a.txt", "a")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")
    monkeypatch.chdir(root)
    monkeypatch.delenv("CONFIRM", raising=False)
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "protocol.file.allow")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "always")
    return root


def test_name_validation():
    for bad in ("", "../x", "A", "a b", "-x", "a/b"):
        with pytest.raises(lane.LaneError):
            lane.valid_name(bad)
    assert lane.valid_name("react-2") == "react-2"


def test_create_list_and_done_cycle(repo, capsys):
    assert lane.main(["new", "demo"]) == 0
    wt = repo / ".worktrees" / "demo"
    assert (wt / "a.txt").is_file() and (wt / ".crepidoma" / "f").is_file()
    exclude = (repo / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert ".worktrees/" in exclude.splitlines()
    assert lane.main(["list"]) == 0
    assert "lane/demo +0/-0 dirty=0 untracked=0" in capsys.readouterr().out

    _write(wt / "new.txt", "n")
    assert lane.main(["done", "demo"]) == 1  # no CONFIRM
    assert "CONFIRM=yes" in capsys.readouterr().err


def test_done_refusals_and_success(repo, monkeypatch, capsys):
    monkeypatch.setenv("CONFIRM", "yes")
    assert lane.main(["new", "demo"]) == 0
    wt = repo / ".worktrees" / "demo"
    _write(wt / "new.txt", "n")
    assert lane.main(["done", "demo"]) == 1  # untracked file
    assert "not clean" in capsys.readouterr().err
    _git(wt, "add", "new.txt")
    _git(wt, "commit", "-q", "-m", "work")
    assert lane.main(["done", "demo"]) == 1  # unmerged
    assert "not merged" in capsys.readouterr().err
    _git(repo, "merge", "-q", "lane/demo")
    assert lane.main(["done", "demo"]) == 0
    assert not wt.exists()
    branches = subprocess.run(
        ["git", "branch", "--list", "lane/*"], capture_output=True, text=True, check=True
    ).stdout
    assert branches.strip() == ""


def test_new_rejects_existing_and_bad_base(repo, capsys):
    assert lane.main(["new", "demo"]) == 0
    assert lane.main(["new", "demo"]) == 1
    assert "already exists" in capsys.readouterr().err
    assert lane.main(["new", "other", "--base=--evil"]) == 1
    assert lane.main(["list"]) == 0
