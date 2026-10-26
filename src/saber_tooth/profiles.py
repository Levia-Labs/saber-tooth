from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    min_hand_gap_s: float
    max_hand_speed: float
    reset_window_s: float
    cross_window_s: float
    vision_window_s: float


@dataclass(frozen=True)
class Profile:
    name: str
    njs: float
    offset: float
    target_nps: float
    grid: float
    allow_doubles: bool
    allow_dots: bool
    error: Limits
    warn: Limits
    gap_beats: float = 8.0


def _p(name, njs, nps, grid, doubles, dots, warn, error) -> Profile:
    return Profile(name, njs, 0.0, nps, grid, doubles, dots, Limits(*error), Limits(*warn))


# fmt: off
_ROWS = (
    # name, njs, nps, grid, doubles, dots, warn limits, error limits
    ("Easy", 10, 1.2, 1.0, False, False,
     (0.75, 4, 1.5, 0.6, 0.5), (0.40, 7, 0.8, 0.35, 0.30)),
    ("Normal", 12, 2.0, 0.5, False, False,
     (0.50, 5, 1.2, 0.5, 0.45), (0.30, 10, 0.6, 0.30, 0.25)),
    ("Hard", 14, 3.2, 0.5, True, False,
     (0.32, 6.5, 0.9, 0.4, 0.40), (0.18, 14, 0.45, 0.25, 0.20)),
    ("Expert", 16, 4.6, 0.25, True, True,
     (0.22, 8, 0.7, 0.3, 0.35), (0.12, 20, 0.35, 0.20, 0.18)),
    ("ExpertPlus", 18, 6.2, 0.25, True, True,
     (0.16, 10, 0.5, 0.25, 0.30), (0.09, 25, 0.30, 0.15, 0.15)),
)

PROFILES: dict[str, Profile] = {r[0]: _p(*r) for r in _ROWS}
# fmt: on
