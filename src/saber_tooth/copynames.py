"""Folder and song names of saber-tooth copies: one " [saber-tooth]" suffix, never doubled."""

import re

FIX_SUFFIX = " [saber-tooth]"
_TAG = r" \[(?:saber-tooth(?: \d+)?|\d+ min|crop[^\]]*)\]"  # copy suffix or legacy length tag
_FIX_ANY = re.compile(rf"(?:{_TAG})+$")
_CROP = re.compile(r" \[(?:\d+ min|crop[^\]]*)\]$")  # legacy crop length tags
_ONE = re.compile(r" \[saber-tooth(?: (\d+))?\]")


def strip_fixed(name: str) -> str:
    """`name` without trailing saber-tooth suffixes and legacy `[N min]`/`[crop ..]` tags."""
    return _FIX_ANY.sub("", name)


def fixed_name(name: str) -> str:
    """`name` with exactly one " [saber-tooth]" suffix."""
    return strip_fixed(name) + FIX_SUFFIX


def is_fixed_copy(name: str) -> bool:
    return _FIX_ANY.search(name) is not None


def strip_crop(name: str) -> str:
    """`name` without a legacy crop length tag."""
    return _CROP.sub("", name)


def split_copy(name: str) -> tuple[str, int, int]:
    """(base, suffix count, last N); legacy tags alone count as one suffix, no tag as 0."""
    m = _FIX_ANY.search(name)
    if not m:
        return name, 0, 0
    ones = _ONE.findall(m.group(0))
    return name[: m.start()], max(len(ones), 1), int(ones[-1] or 1) if ones else 1


def chain_names(listing: list[str], folders: list[str]) -> list[str]:
    """Names in `listing` in the same chain (original and its copies) as any of `folders`,
    plus `folders` themselves; sorted, no duplicates."""
    bases = {strip_fixed(f) for f in folders}
    found = {n for n in listing if strip_fixed(n) in bases}
    return sorted(found | set(folders))
