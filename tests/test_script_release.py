"""Tests for the pure and mocked parts of scripts/release.py; no docker, no network."""

import urllib.error

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tests.script_loader import load

release = load("release")


def test_read_version():
    assert release.read_version('[project]\nname = "x"\nversion = "1.2.3"\n') == "1.2.3"


def test_read_version_missing():
    with pytest.raises(KeyError):
        release.read_version('[project]\nname = "x"\n')


def test_real_pyproject_has_a_version():
    text = (release.ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert release.read_version(text)


@given(st.from_regex(r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}", fullmatch=True))
def test_tags_always_pair_version_with_latest(version):
    assert release.image_tags(version) == [
        f"levialabs/sabertooth:{version}",
        "levialabs/sabertooth:latest",
    ]


@given(st.text(min_size=1, max_size=20), st.text(min_size=1, max_size=40))
def test_label_args_pair_each_label(version, revision):
    args = release.label_args(version, revision, "2026-01-01T00:00:00Z")
    assert args[0::2] == ["--label"] * 4
    assert f"org.opencontainers.image.version={version}" in args
    assert f"org.opencontainers.image.revision={revision}" in args
    assert f"org.opencontainers.image.source={release.SOURCE}" in args


def test_failures_lists_only_nonempty():
    assert release.failures({"a": "", "b": "bad"}) == ["b: bad"]
    assert release.failures({"a": ""}) == []


def test_hub_tag_free_on_404():
    def fetch(url):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    assert release.hub_tag_reason("1.0.0", fetch) == ""


def test_hub_tag_taken_on_200():
    assert "already published" in release.hub_tag_reason("1.0.0", lambda url: 200)


def test_hub_tag_url_and_odd_status():
    seen = []

    def fetch(url):
        seen.append(url)
        return 500

    assert "500" in release.hub_tag_reason("1.0.0", fetch)
    assert seen == [f"{release.HUB_TAGS}/1.0.0/"]


def test_hub_tag_unreachable_fails():
    def fetch(url):
        raise urllib.error.URLError("down")

    assert "unreachable" in release.hub_tag_reason("1.0.0", fetch)


def test_check_clean_with_mocked_git(monkeypatch):
    monkeypatch.setattr(release, "run", lambda cmd, check=False: (0, " M a\n?? b"))
    assert release.check_clean() == "2 changed paths"
    monkeypatch.setattr(release, "run", lambda cmd, check=False: (0, ""))
    assert release.check_clean() == ""


def test_check_branch_and_git_tag(monkeypatch):
    monkeypatch.setattr(release, "run", lambda cmd, check=False: (0, "feat"))
    assert "not main" in release.check_branch()
    assert "exists" in release.check_git_tag("1.0.0")


def test_hub_status_refuses_other_hosts():
    with pytest.raises(ValueError):
        release.hub_status("file:///etc/passwd")


def test_parse_digest_reads_the_digest_line_not_the_name():
    # imagetools ignores --format on single-platform manifests and prints Name, MediaType, Digest.
    sha = "sha256:" + "a" * 64
    text = f"Name:      docker.io/x/y:latest\nMediaType: application/json\nDigest:    {sha}\n"
    assert release.parse_digest(text) == sha
    assert release.parse_digest(sha + "\n") == sha
