"""Tests for scripts/lane_apply.py against temporary git repositories."""

import subprocess

import pytest

from tests.script_loader import load

lane_apply = load("lane_apply")


def _git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


@pytest.fixture
def pair(tmp_path):
    main = tmp_path / "main"
    main.mkdir()
    _git(main, "init", "-q", "-b", "main")
    _git(main, "config", "user.email", "t@example.com")
    _git(main, "config", "user.name", "t")
    (main / "a.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")
    (main / "b.txt").write_text("keep\n", encoding="utf-8")
    _git(main, "add", ".")
    _git(main, "commit", "-q", "-m", "init")
    wt = tmp_path / "wt"
    _git(main, "worktree", "add", "-q", "-b", "lane/x", str(wt))
    (wt / "a.txt").write_text("one\nTWO\nthree\n", encoding="utf-8")
    (wt / "b.txt").write_text("changed\n", encoding="utf-8")
    (wt / "new.txt").write_text("fresh\n", encoding="utf-8")
    return main, wt


def test_parse_name_status():
    raw = b"M\0a.txt\0A\0new.txt\0"
    assert lane_apply.parse_name_status(raw) == ["M a.txt", "A new.txt"]
    assert lane_apply.parse_name_status(b"") == []


def test_failure_lines_capped():
    text = "\n".join(f"l{i}" for i in range(50)).encode()
    assert len(lane_apply.failure_lines(text)) == 20


def test_apply_all(pair, monkeypatch, capsys):
    main, wt = pair
    monkeypatch.chdir(main)
    assert lane_apply.main([str(wt)]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "M a.txt",
        "M b.txt",
        "A new.txt",
        "applied 3 files",
    ]
    assert (main / "a.txt").read_text(encoding="utf-8") == "one\nTWO\nthree\n"
    assert (main / "new.txt").read_text(encoding="utf-8") == "fresh\n"
    assert (wt / "new.txt").read_text(encoding="utf-8") == "fresh\n"


def test_check_leaves_tree(pair, monkeypatch, capsys):
    main, wt = pair
    monkeypatch.chdir(main)
    assert lane_apply.main([str(wt), "--check"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "applied 3 files"
    assert (main / "a.txt").read_text(encoding="utf-8") == "one\ntwo\nthree\n"
    assert not (main / "new.txt").exists()


def test_paths_filter(pair, monkeypatch, capsys):
    main, wt = pair
    monkeypatch.chdir(main)
    assert lane_apply.main([str(wt), "--paths", "new.txt", "b.txt"]) == 0
    assert capsys.readouterr().out.splitlines() == ["M b.txt", "A new.txt", "applied 2 files"]
    assert (main / "a.txt").read_text(encoding="utf-8") == "one\ntwo\nthree\n"
    assert (main / "b.txt").read_text(encoding="utf-8") == "changed\n"


def test_conflict_exits_1(pair, monkeypatch, capsys):
    main, wt = pair
    (main / "a.txt").write_text("one\nOTHER\nthree\n", encoding="utf-8")
    monkeypatch.chdir(main)
    assert lane_apply.main([str(wt)]) == 1
    err = capsys.readouterr().err
    assert "a.txt" in err
    assert not (main / "new.txt").exists()
    assert (main / "a.txt").read_text(encoding="utf-8") == "one\nOTHER\nthree\n"


def test_missing_worktree(pair, monkeypatch, tmp_path):
    main, _ = pair
    monkeypatch.chdir(main)
    assert lane_apply.main([str(tmp_path / "nope")]) == 1
