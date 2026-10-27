"""Tests for scripts/commit.py: pure helpers, fake runners and one real temp repository."""

import subprocess

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tests.script_loader import load

cm = load("commit")


def done(rc=0, out="", err=""):
    return subprocess.CompletedProcess([], rc, out, err)


@given(st.text(min_size=1, max_size=80).filter(lambda s: s.strip()))
def test_trailer_appended_exactly_once(message):
    once = cm.build_message(message)
    assert once.count(cm.TRAILER) == 1
    assert cm.build_message(once) == once


def test_split_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in ("a.py", "b.md", "c.txt"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    assert cm.split_paths(["a.py", "b.md", "c.txt", "gone.py"]) == (["a.py"], ["b.md"])


def test_check_paths_rejects_options_and_traversal():
    for bad in ([], ["-x"], ["../a"], ["a/../../b"]):
        with pytest.raises(ValueError):
            cm.check_paths(bad)
    cm.check_paths(["a/b.py"])


def test_commit_retries_once_after_hook_failure():
    calls = []

    def runner(argv):
        calls.append(argv[:2])
        if argv[1] == "commit":
            return done(1 if calls.count(["git", "commit"]) == 1 else 0, err="hook modified")
        return done()

    assert cm.commit("msg", ["a.py"], runner)[0] == 0
    assert calls == [["git", "add"], ["git", "commit"]] * 2


def test_commit_gives_up_after_two_failures():
    rc, out = cm.commit(
        "m", ["a"], lambda argv: done(1, err="bad") if argv[1] == "commit" else done()
    )
    assert rc == 1 and "bad" in out


def test_never_skips_hooks():
    seen = []
    cm.commit("m", ["a"], lambda argv: seen.append(argv) or done())
    assert not any("--no-verify" in a or "-n" in a for a in seen)


def test_format_warns_when_tools_fail(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in ("a.py", "b.md"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    assert len(cm.format_paths(["a.py", "b.md"], lambda argv: done(1))) == 2
    assert cm.format_paths(["a.py"], lambda argv: done(0)) == []


def test_real_repo_commit_only_named_paths(tmp_path, monkeypatch):
    def git(*a):
        base = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
        return subprocess.run([*base, *a], cwd=tmp_path, capture_output=True, text=True, check=True)

    git("init", "-q", "-b", "main")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    git("add", "b.txt")  # staged by someone else; must stay out of the commit

    def run(argv):
        if argv[0] == "git":
            argv = [*argv[:1], "-c", "user.name=t", "-c", "user.email=t@t", *argv[1:]]
        return subprocess.run(argv, capture_output=True, text=True, check=False)

    rc, _ = cm.commit("feat: a", ["a.txt"], run)
    assert rc == 0 and cm.verify("feat: a", run)
    assert git("show", "--stat", "--format=%B", "HEAD").stdout.count("a.txt") == 1
    assert "b.txt" not in git("show", "--name-only", "--format=", "HEAD").stdout
    assert cm.TRAILER in git("log", "-1", "--format=%B").stdout
    assert cm.verify("other", run) is None


def test_resolve_argv_uses_path_match(monkeypatch):
    monkeypatch.setattr(cm.shutil, "which", lambda n: f"C:/bin/{n}.cmd" if n == "npx" else None)
    assert cm.resolve_argv(["npx", "--no-install", "prettier"]) == [
        "C:/bin/npx.cmd",
        "--no-install",
        "prettier",
    ]
    assert cm.resolve_argv(["ruff", "format"]) == ["ruff", "format"]


def test_run_executes_the_resolved_executable(monkeypatch):
    seen = []
    monkeypatch.setattr(cm.shutil, "which", lambda n: f"/x/{n}.cmd")
    monkeypatch.setattr(cm.subprocess, "run", lambda argv, **kw: seen.append(argv) or done())
    cm.run(["npx", "prettier"])
    assert seen == [["/x/npx.cmd", "prettier"]]
