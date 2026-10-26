from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

DIFFICULTIES = ("Easy", "Normal", "Hard", "Expert", "ExpertPlus")
RANKS = {"Easy": 1, "Normal": 3, "Hard": 5, "Expert": 7, "ExpertPlus": 9}


class Color(IntEnum):
    RED = 0
    BLUE = 1


class Cut(IntEnum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    UP_LEFT = 4
    UP_RIGHT = 5
    DOWN_LEFT = 6
    DOWN_RIGHT = 7
    ANY = 8


# Unit swing vectors in grid space (x right, y up); ANY has no direction.
CUT_VECTORS: dict[Cut, tuple[float, float]] = {
    Cut.UP: (0, 1),
    Cut.DOWN: (0, -1),
    Cut.LEFT: (-1, 0),
    Cut.RIGHT: (1, 0),
    Cut.UP_LEFT: (-0.7071, 0.7071),
    Cut.UP_RIGHT: (0.7071, 0.7071),
    Cut.DOWN_LEFT: (-0.7071, -0.7071),
    Cut.DOWN_RIGHT: (0.7071, -0.7071),
}
OPPOSITE = {
    Cut.UP: Cut.DOWN,
    Cut.DOWN: Cut.UP,
    Cut.LEFT: Cut.RIGHT,
    Cut.RIGHT: Cut.LEFT,
    Cut.UP_LEFT: Cut.DOWN_RIGHT,
    Cut.DOWN_RIGHT: Cut.UP_LEFT,
    Cut.UP_RIGHT: Cut.DOWN_LEFT,
    Cut.DOWN_LEFT: Cut.UP_RIGHT,
    Cut.ANY: Cut.ANY,
}


@dataclass(frozen=True, order=True)
class Note:
    beat: float
    x: int
    y: int
    color: Color
    cut: Cut
    angle: int = 0


@dataclass(frozen=True, order=True)
class Bomb:
    beat: float
    x: int
    y: int


@dataclass(frozen=True, order=True)
class Wall:
    beat: float
    x: int
    y: int
    duration: float
    width: int
    height: int


@dataclass(frozen=True, order=True)
class BasicEvent:
    beat: float
    type: int
    value: int
    float_value: float = 1.0


@dataclass(frozen=True, order=True)
class BpmEvent:
    beat: float
    bpm: float


@dataclass
class Difficulty:
    name: str
    njs: float
    offset: float
    notes: list[Note] = field(default_factory=list)
    bombs: list[Bomb] = field(default_factory=list)
    walls: list[Wall] = field(default_factory=list)
    events: list[BasicEvent] = field(default_factory=list)
    boosts: list[tuple[float, bool]] = field(default_factory=list)
    bpm_events: list[BpmEvent] = field(default_factory=list)
    # Raw v3 lists kept verbatim: event box groups, sliders, burst sliders.
    raw: dict[str, Any] = field(default_factory=dict)
    filename: str = ""


@dataclass(frozen=True)
class ColorScheme:
    id: str
    # saberAColor, saberBColor, environmentColor0, ... -> {r, g, b, a}
    colors: dict[str, dict[str, float]]


@dataclass
class MapInfo:
    song_name: str
    sub_name: str
    author: str
    mapper: str
    bpm: float
    song_file: str
    cover_file: str
    preview_start: float
    preview_duration: float
    environment: str
    color_scheme: ColorScheme | None = None


@dataclass
class Beatmap:
    info: MapInfo
    difficulties: dict[str, Difficulty]
    folder_name: str = ""
