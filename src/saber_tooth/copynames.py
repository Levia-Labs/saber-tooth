"""Folder and song names of saber-tooth copies: one " [saber-tooth]" suffix, never doubled."""

import re

FIX_SUFFIX = " [saber-tooth]"
_FIX_ANY = re.compile(r"(?: \[saber-tooth(?: \d+)?\])+$")
_CROP = re.compile(r" \[(?:1 min|2 min|crop [^\]]*)\]$")  # legacy crop length tags


def strip_fixed(name: str) -> str:
    """`name` without any trailing saber-tooth suffixes (doubled or numbered ones too)."""
    return _FIX_ANY.sub("", name)


def fixed_name(name: str) -> str:
    """`name` with exactly one " [saber-tooth]" suffix."""
    return strip_fixed(name) + FIX_SUFFIX


def is_fixed_copy(name: str) -> bool:
    return _FIX_ANY.search(name) is not None


def strip_crop(name: str) -> str:
    """`name` without a legacy crop length tag."""
    return _CROP.sub("", name)


def chain_names(listing: list[str], folders: list[str]) -> list[str]:
    """Names in `listing` in the same chain (original and its copies) as any of `folders`,
    plus `folders` themselves; sorted, no duplicates."""
    bases = {strip_fixed(f) for f in folders}
    found = {n for n in listing if strip_fixed(n) in bases}
    return sorted(found | set(folders))
