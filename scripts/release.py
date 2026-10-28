#!/usr/bin/env python3
"""Release levialabs/sabertooth: preflight, build, verify, and with --apply publish.

Standard library only. The version comes from pyproject.toml; the image gets the tags
`<version>` and `latest`. A published version tag is never overwritten.

Usage:
  python scripts/release.py            preflight, build, verify, then print what --apply does
  python scripts/release.py --apply    push both tags, confirm digests, tag git, check the page
"""

import argparse
import datetime
import re
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "levialabs/sabertooth"
LOCAL_IMAGE = "saber-tooth:latest"
SOURCE = "https://github.com/Levia-Labs/saber-tooth"
HUB_TAGS = f"https://hub.docker.com/v2/repositories/{IMAGE}/tags"


def read_version(text: str) -> str:
    """The project version from pyproject.toml text."""
    version = tomllib.loads(text)["project"]["version"]
    if not isinstance(version, str) or not version:
        raise ValueError("pyproject.toml has no project.version")
    return version


def image_tags(version: str) -> list[str]:
    return [f"{IMAGE}:{version}", f"{IMAGE}:latest"]


def label_args(version: str, revision: str, created: str) -> list[str]:
    """The `--label` arguments for `docker build`: OCI version, revision, source, created."""
    labels = {
        "org.opencontainers.image.version": version,
        "org.opencontainers.image.revision": revision,
        "org.opencontainers.image.source": SOURCE,
        "org.opencontainers.image.created": created,
    }
    return [arg for key, value in labels.items() for arg in ("--label", f"{key}={value}")]


def failures(results: dict[str, str]) -> list[str]:
    """One `name: reason` line per preflight check whose reason is not empty."""
    return [f"{name}: {reason}" for name, reason in results.items() if reason]


def run(cmd: list[str], check: bool = False) -> tuple[int, str]:
    found = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False
    )
    out = (found.stdout + found.stderr).strip()
    if check and found.returncode:
        raise SystemExit(f"failed: {' '.join(cmd)}\n{out[-600:]}")
    return found.returncode, out


def check_clean() -> str:
    out = run(["git", "status", "--porcelain"])[1]
    return f"{len(out.splitlines())} changed paths" if out else ""


def check_branch() -> str:
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])[1]
    return "" if branch == "main" else f"on {branch}, not main"


def check_origin() -> str:
    code, out = run(["git", "fetch", "origin", "main"])
    if code:
        return f"git fetch failed: {out[-120:]}"
    head, origin = run(["git", "rev-parse", "HEAD"])[1], run(["git", "rev-parse", "origin/main"])[1]
    return "" if head == origin else "HEAD differs from origin/main"


def check_daemon() -> str:
    return "" if run(["docker", "info"])[0] == 0 else "docker daemon is not running"


def hub_tag_reason(version: str, fetch: Callable[[str], int]) -> str:
    """Empty when the version tag is free on Docker Hub (404), else why not."""
    try:
        status = fetch(f"{HUB_TAGS}/{version}/")
    except urllib.error.HTTPError as exc:
        status = exc.code
    except (urllib.error.URLError, OSError) as exc:
        return f"Docker Hub unreachable: {exc}"
    if status == 404:
        return ""
    return f"{IMAGE}:{version} already published" if status == 200 else f"Hub answered {status}"


def hub_status(url: str) -> int:
    if not url.startswith("https://hub.docker.com/"):
        raise ValueError("refusing a URL outside Docker Hub")
    req = urllib.request.Request(url, headers={"User-Agent": "saber-tooth-dev"})  # noqa: S310  # nosec B310
    # nosemgrep: dynamic-urllib-use-detected - URL checked above to be on Docker Hub
    with urllib.request.urlopen(req, timeout=30) as response:  # noqa: S310  # nosec B310
        return response.status


def check_git_tag(version: str) -> str:
    return f"git tag v{version} exists" if run(["git", "tag", "--list", f"v{version}"])[1] else ""


def preflight(version: str) -> dict[str, str]:
    return {
        "tree clean": check_clean(),
        "on main": check_branch(),
        "HEAD is origin/main": check_origin(),
        "docker daemon": check_daemon(),
        "hub tag free": hub_tag_reason(version, hub_status),
        "git tag free": check_git_tag(version),
    }


def build(version: str) -> None:
    revision = run(["git", "rev-parse", "HEAD"], check=True)[1]
    created = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    cmd = ["docker", "build", "--pull", *label_args(version, revision, created)]
    for tag in [*image_tags(version), LOCAL_IMAGE]:
        cmd += ["-t", tag]
    run([*cmd, "."], check=True)


def verify() -> None:
    run(["docker", "compose", "up", "-d"], check=True)
    code, out = run([sys.executable, "scripts/smoke.py"])
    print(out)
    if code:
        raise SystemExit("smoke check failed; nothing was published")


def parse_digest(text: str) -> str:
    # imagetools ignores --format on single-platform manifests and prints Name, MediaType and
    # Digest lines; the Name line differs per tag, so comparing whole outputs never matches.
    match = re.search(r"sha256:[0-9a-f]{64}", text)
    if not match:
        raise SystemExit(f"no digest in imagetools output: {text.strip()[:200]}")
    return match.group(0)


def digest(tag: str) -> str:
    cmd = ["docker", "buildx", "imagetools", "inspect", tag, "--format", "{{.Manifest.Digest}}"]
    return parse_digest(run(cmd, check=True)[1])


def apply(version: str) -> None:
    tags = image_tags(version)
    for tag in tags:
        run(["docker", "push", tag], check=True)
    digests = [digest(tag) for tag in tags]
    if len(set(digests)) != 1:
        raise SystemExit(f"remote digests differ: {digests}")
    print(f"digest {digests[0]}")
    run(["git", "tag", "-a", f"v{version}", "-m", f"saber-tooth {version}"], check=True)
    run(["git", "push", "origin", f"refs/tags/v{version}"], check=True)
    print(f"tagged and pushed v{version}")
    out = run([sys.executable, "scripts/hub.py"])[1]
    print(out)
    if "differs" in out:
        print("next: task st:hub:publish (run by a person)")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=(__doc__ or "").partition("\n")[0])
    parser.add_argument("--apply", action="store_true", help="publish instead of a dry run")
    args = parser.parse_args()

    version = read_version((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    bad = failures(preflight(version))
    if bad:
        print(f"release {version}: preflight failed")
        print("\n".join(f"  {line}" for line in bad))
        return 1
    print(f"release {version}: preflight ok")
    build(version)
    verify()
    tags = image_tags(version)
    if not args.apply:
        print(f"dry run done. --apply would push {', '.join(tags)}, confirm both digests are")
        print(f"equal, create and push git tag v{version}, then check the Docker Hub page.")
        return 0
    apply(version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
