"""Tests for scripts/review_diff.py using a temporary git repository."""

import subprocess
import sys

import pytest

from tests.script_loader import load

rd = load("review_diff")


def _git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True)


def _write(path, text):
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    _git(tmp_path, "init", "-q", "-b", "main")
    _write(tmp_path / "a.txt", "1\n")
    _write(tmp_path / "uv.lock", "1\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "one")
    _write(tmp_path / "a.txt", "2\n")
    _write(tmp_path / "uv.lock", "2\n")
    _write(tmp_path / "b.txt", "b\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "two")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_validate_range_rejects_options_and_spaces():
    for bad in ("--output=x", "a b", "a;b", "", "-x..y"):
        with pytest.raises(ValueError):
            rd.validate_range(bad)
    assert rd.validate_range("main..HEAD") == "main..HEAD"
    assert rd.validate_range("HEAD~2") == "HEAD~2"


def test_out_name():
    assert rd.out_name("main..feat/x") == "review-main..feat_x.diff"
    assert rd.out_name("HEAD~1") == "review-HEAD~1..HEAD.diff"


def test_writes_diff_without_lockfiles(repo, capsys):
    assert rd.main(["HEAD~1..HEAD", "--out", "out"]) == 0
    text = capsys.readouterr().out
    assert "files=2 commits=1" in text
    body = (repo / "out" / "review-HEAD~1..HEAD.diff").read_text(encoding="utf-8")
    assert "a.txt" in body and "uv.lock" not in body


def test_extra_exclude(repo, capsys):
    assert rd.main(["HEAD~1..HEAD", "--out", "out", "--exclude", "b.txt"]) == 0
    assert "files=1" in capsys.readouterr().out


def test_bad_range_fails(repo, capsys):
    assert rd.main(["nope..HEAD", "--out", "out"]) == 1
    assert "review-diff failed" in capsys.readouterr().err


def test_cli_help_runs():
    res = subprocess.run(
        [sys.executable, rd.__file__, "-h"], capture_output=True, text=True, check=True
    )
    assert "range" in res.stdout
