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
