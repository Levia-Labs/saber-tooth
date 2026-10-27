"""Tests for scripts/sync.py parsing and formatting with a fake git runner."""

from tests.script_loader import load

sync = load("sync")

PORCELAIN = """worktree /r
HEAD abc
branch refs/heads/main

worktree /r/.worktrees/x
HEAD def
detached
"""


def fake(answers):
    def run(path, *args):
        key = args[-1] if args[0] == "rev-parse" else args[0]
        return answers.get((path, key))

    return run


def test_parse_worktrees():
    assert sync.parse_worktrees(PORCELAIN) == [("/r", "main"), ("/r/.worktrees/x", "(detached)")]
    assert sync.parse_worktrees("") == []


def test_parse_status_counts():
    assert sync.parse_status(" M a\n?? b\nA  c\n?? d\n") == (2, 2)
    assert sync.parse_status("") == (0, 0)


def test_ahead_behind():
    assert sync.ahead_behind("1\t3") == "+3/-1"
    assert sync.ahead_behind(None) == "no upstream"


def test_describe_match():
    run = fake(
        {
            ("/r", "status"): " M a\n?? b",
            ("/r", "rev-list"): "0\t2",
            ("/r/.crepidoma", "HEAD"): "aaa1111",
            ("/r/.crepidoma", "origin/main"): "aaa1111",
        }
    )
    line = sync.describe("/r", "main", run)
    assert line == "/r [main] +2/-0 dirty=1 untracked=1 .crepidoma aaa1111 match"


def test_describe_differs_and_missing():
    run = fake({("/r/.crepidoma", "HEAD"): "aaa1111", ("/r/.crepidoma", "origin/main"): "bbb2222"})
    line = sync.describe("/r", "main", run)
    assert "differs(bbb2222)" in line and "no upstream" in line
    assert sync.submodule_state("/q", lambda *a: None) == ".crepidoma missing"
