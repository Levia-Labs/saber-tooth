"""Collapse every song chain in the library to one map named "Title [saber-tooth]".

A chain is an original folder F plus every folder named F followed by one or more
" [saber-tooth]" / " [saber-tooth N]" suffixes; generated maps (folder "st-...") are their own
chain. Originals and generated maps are never deleted. Per chain one copy is kept (newest
generation, duration >= 30 s, then cropped, then highest N) and the other copies are deleted; the
kept copy and generated maps are renamed with keep_folder. Dry run by default; --apply deletes
first, then renames (data-deleting, hard delete of copies only).
Talks only to the running API. --levels DIR adds folders the API list hides (id = first 12 hex of
sha256 of the folder name).

Usage: uv run python scripts/library_tidy.py [--base URL] [--levels DIR] [--originals keep|drop]
       [--apply]
--originals drop also deletes the original of each chain that has a copy (no keep_folder).
--apply requires --levels: each folder must pass the strict map-folder guard (only map folders
are ever deleted) or it is skipped and counted as refused.
Exit: 0 ok, 1 a request failed, 2 usage.
"""

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from saber_tooth.map_folder_guard import check_map_folder

Request = Callable[[str, str, bytes | None], tuple[int, bytes]]
SUFFIX_RE = re.compile(r"^(.*?)((?: \[saber-tooth(?: \d+)?\])+)$", re.S)
ONE_SUFFIX_RE = re.compile(r" \[saber-tooth(?: (\d+))?\]")
TAG_RE = re.compile(r"\s*\[(?:saber-tooth(?: \d+)?|crop[^\]]*|\d+ min)\]")
CROP_RE = re.compile(r"\[crop[^\]]*\]")
MIN_DURATION = 30.0


@dataclass(frozen=True)
class Item:
    id: str
    folder: str
    title: str | None = None
    duration_s: float | None = None


@dataclass(frozen=True)
class Plan:
    chains: int
    keep: tuple[Item, ...]
    delete: tuple[Item, ...]
    rename: tuple[tuple[Item, str], ...]
    drop_ids: frozenset[str] = frozenset()


def map_id_for(folder: str) -> str:
    return hashlib.sha256(folder.encode("utf-8")).hexdigest()[:12]


def chain_key(folder: str) -> tuple[str, int, int]:
    """(chain key, suffix count, last N); generated maps and originals have count 0."""
    if folder.startswith("st-"):
        return folder, 0, 0
    m = SUFFIX_RE.match(folder)
    if not m:
        return folder, 0, 0
    suffixes = ONE_SUFFIX_RE.findall(m.group(2))
    return m.group(1), len(suffixes), int(suffixes[-1] or 1)


def clean_title(title: str) -> str:
    return " ".join(TAG_RE.sub("", title).split())


def _cropped(item: Item) -> bool:
    return bool(item.title and CROP_RE.search(item.title))


def pick(copies: list[Item]) -> Item:
    top = max(chain_key(i.folder)[1] for i in copies)
    newest = [i for i in copies if chain_key(i.folder)[1] == top]
    return max(
        newest,
        key=lambda i: (
            (i.duration_s or 0) >= MIN_DURATION,
            _cropped(i),
            chain_key(i.folder)[2],
            i.folder,
        ),
    )


def plan(items: list[Item], originals: str = "keep") -> Plan:
    chains: dict[str, list[Item]] = {}
    for item in items:
        chains.setdefault(chain_key(item.folder)[0], []).append(item)
    keep, delete, rename, drop_ids = [], [], [], set()
    for key in sorted(chains):
        members = chains[key]
        copies = [i for i in members if chain_key(i.folder)[1] > 0]
        others = [i for i in members if i not in copies]
        drop = originals == "drop" and bool(copies)
        (delete if drop else keep).extend(others)
        rename.extend(
            (i, new_name(i)) for i in members if i.folder.startswith("st-") and needs_rename(i)
        )
        if not copies:
            continue
        kept = pick(copies)
        keep.append(kept)
        if drop:
            drop_ids.add(kept.id)
        delete.extend(sorted((i for i in copies if i is not kept), key=lambda i: i.folder))
        if needs_rename(kept):
            rename.append((kept, new_name(kept)))
    return Plan(len(chains), tuple(keep), tuple(delete), tuple(rename), frozenset(drop_ids))


def new_name(item: Item) -> str:
    return clean_title(item.title or "") + " [saber-tooth]"


def needs_rename(item: Item) -> bool:
    return item.title is not None and new_name(item) != item.title


def http(method: str, url: str, body: bytes | None = None) -> tuple[int, bytes]:
    if not url.startswith(("http://", "https://")):
        return 0, b""
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(url, data=body, headers=headers, method=method)  # noqa: S310  # nosec B310
    try:
        # nosemgrep: dynamic-urllib-use-detected - scheme checked above
        with urllib.request.urlopen(req, timeout=60) as res:  # noqa: S310  # nosec B310
            return res.status, res.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""
    except (urllib.error.URLError, OSError):
        return 0, b""


def fetch_items(base: str, request: Request = http) -> list[Item]:
    items: list[Item] = []
    offset = 0
    while True:
        status, raw = request("GET", f"{base}/api/maps?limit=100&offset={offset}", None)
        if status != 200:
            raise RuntimeError(f"GET /api/maps offset={offset} returned {status}")
        rows = json.loads(raw).get("items", [])
        items += [Item(r["id"], r["folder"], r.get("title"), r.get("duration_s")) for r in rows]
        if len(rows) < 100:
            return items
        offset += 100


def with_hidden(items: list[Item], folders: list[str]) -> list[Item]:
    known = {i.folder for i in items}
    return items + [Item(map_id_for(f), f) for f in sorted(folders) if f not in known]


def level_folders(levels: Path) -> list[str]:
    return [p.name for p in levels.iterdir() if p.is_dir()]


def apply_plan(
    base: str, result: Plan, request: Request = http, cap: int = 20, levels: Path | None = None
) -> tuple[int, list[str], int]:
    """Deletes first, then renames; returns (failure count, up to `cap` lines, refused count).

    Every folder is checked locally by the map-folder guard before its DELETE; a refused folder is
    skipped and reported, never deleted. Without `levels` nothing is deleted.
    """
    failures: list[str] = []
    refused = 0
    for item in result.delete:
        reasons = (
            check_map_folder(levels / item.folder, levels, item.id)
            if levels
            else ["no levels folder given"]
        )
        if reasons:
            refused += 1
            failures.append(f"refused {item.id} {item.folder}: {'; '.join(reasons)}")
            continue
        status, _ = request("DELETE", f"{base}/api/maps/{item.id}", None)
        if status not in (200, 204, 404):
            failures.append(f"delete {item.id} {item.folder}: HTTP {status}")
    for item, name in result.rename:
        payload = {"name": name}
        if item.id not in result.drop_ids:
            payload["keep_folder"] = True
        body = json.dumps(payload).encode("utf-8")
        status, _ = request("PATCH", f"{base}/api/maps/{item.id}", body)
        if status != 200:
            failures.append(f"rename {item.id} {item.folder}: HTTP {status}")
    failed = [f for f in failures if not f.startswith("refused ")]
    return len(failed), failures[:cap], refused


def summary(result: Plan) -> str:
    return (
        f"chains={result.chains} keep={len(result.keep)} delete={len(result.delete)} "
        f"rename={len(result.rename)}"
    )


def examples(result: Plan, top: int = 10) -> list[str]:
    lines = [f"delete {i.folder}" for i in result.delete]
    lines += [f"rename {i.folder} -> {n}" for i, n in result.rename]
    return lines[:top]


def main(argv: list[str] | None = None, request: Request = http) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--base", default="http://127.0.0.1:8100")
    ap.add_argument("--levels", type=Path, help="CustomLevels folder to find hidden maps")
    ap.add_argument("--originals", choices=("keep", "drop"), default="keep")
    ap.add_argument("--apply", action="store_true", help="execute the deletes and renames")
    args = ap.parse_args(argv)
    if args.apply and not args.levels:
        print("FAIL --apply requires --levels so every folder can be checked before deletion")
        return 2
    try:
        items = fetch_items(args.base, request)
        if args.levels:
            items = with_hidden(items, level_folders(args.levels))
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"FAIL {exc}")
        return 1
    result = plan(items, args.originals)
    print(summary(result))
    if not args.apply:
        for line in examples(result):
            print(line)
        return 0
    count, lines, refused = apply_plan(args.base, result, request, levels=args.levels)
    for line in lines:
        print(line)
    print(f"failed={count} refused={refused}")
    return 1 if count else 0


if __name__ == "__main__":
    sys.exit(main())
