"""Mapping Extensions precision encoding for walls: decode raw values to lane units.

ME stores a precise value `v` as `v >= 1000 -> v / 1000 - 1` and `v <= -1000 -> v / 1000 + 1`;
anything in between is a vanilla value and stays as it is. Walls carry it in x, y, width and
height. Notes with such positions stay unsupported (see mapio.vanilla).
"""

from saber_tooth.model import Wall

PRECISION = 1000


def is_precise(v: float) -> bool:
    return abs(v) >= PRECISION


def decode(v: float) -> float:
    """Raw ME value to lanes; vanilla values come back unchanged.

    Spec: https://github.com/Kylemc1413/MappingExtensions/blob/master/README-Beatmapv2.md
    (a width <= -1000 is not specified there: decoded symmetrically, and such walls are stripped).
    """
    if v >= PRECISION:
        return v / PRECISION - 1
    if v <= -PRECISION:
        return v / PRECISION + 1
    return v


def encode(v: float) -> int:
    """Lanes to a raw ME value (the inverse of decode, to 1/1000 lane)."""
    return round((v + 1) * PRECISION) if v >= 0 else round((v - 1) * PRECISION)


WALL_ROWS = 5  # a normal full-height wall is 5 grid rows tall
TYPE_RANGE_2 = 4001  # v2 `_type` from here: height * 1000 + startHeight + 4001


def v2_type_geometry(kind: int) -> tuple[float, float]:
    """(y, height) in grid rows of a v2 obstacle `_type`.

    Spec: https://github.com/Kylemc1413/MappingExtensions/blob/master/README-Beatmapv2.md
    0 full, 1 crouch. 1000..4000: precise height (_type - 1000) / 1000 wall heights from the
    floor. 4001 and up: height = (_type - 4001) // 1000 (1000 = one wall height) and start
    height = (_type - 4001) % 1000 (250 = one wall height up); both scaled to rows.
    """
    if kind >= TYPE_RANGE_2:
        height, start = divmod(kind - TYPE_RANGE_2, PRECISION)
        return start / 250 * WALL_ROWS, height / PRECISION * WALL_ROWS
    if kind >= PRECISION:
        return 0, (kind - PRECISION) / PRECISION * WALL_ROWS
    return (2, 3) if kind == 1 else (0, 5)


def make_wall(
    beat: float, x: float, y: float, duration: float, w: float, h: float, me: bool = False
) -> Wall:
    """A Wall from raw values; flagged `me` with decoded geometry when any value is precise."""
    if not me and not any(is_precise(v) for v in (x, y, w, h)):
        return Wall(beat, int(x), int(y), duration, int(w), int(h))
    return Wall(beat, decode(x), decode(y), duration, decode(w), decode(h), True)
