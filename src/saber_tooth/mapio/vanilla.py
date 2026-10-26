"""Vanilla-only guards: Mapping Extensions and Noodle positions are not supported."""

from saber_tooth.mapio.errors import MapParseError
from saber_tooth.model import Cut

_MSG = "Mapping Extensions/Noodle positions not supported"


def vanilla_cell(x: int, y: int) -> tuple[int, int]:
    """Return (x, y) when it lies on the 4x3 grid; raise MapParseError otherwise."""
    if not (0 <= x <= 3 and 0 <= y <= 2):
        raise MapParseError(f"{_MSG}: cell ({x}, {y})")
    return x, y


def vanilla_cut(direction: int) -> Cut:
    """Return the Cut for a direction 0-8; raise MapParseError otherwise."""
    if not 0 <= direction <= 8:
        raise MapParseError(f"{_MSG}: cut direction {direction}")
    return Cut(direction)
