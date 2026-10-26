"""Thresholds shared by the checks and the generator so the two cannot drift apart."""

import math

VISION_MIN_DT = 0.05  # notes closer than this to a centre note are read as one group
PARITY_DOT = 0.1  # consecutive swings with a dot product above this repeat a direction
MIN_GAP_DENSITY = 1.5  # weighted onsets per second above which an empty gap is reported


def cells_per_second(end: tuple[float, float], start: tuple[float, float], dt: float) -> float:
    """Hand travel speed between the end of one swing and the start of the next."""
    return math.dist(end, start) / dt
