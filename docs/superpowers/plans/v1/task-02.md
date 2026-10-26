### Task 2: Core model and timing

**Files:**

- Create: `src/saber_tooth/model.py`, `src/saber_tooth/timing.py`
- Test: `tests/test_timing.py`

**Interfaces:**

- Produces: `Color`, `Cut`, `Note`, `Bomb`, `Wall`, `BasicEvent`, `BpmEvent`, `Difficulty`, `ColorScheme`, `MapInfo`, `Beatmap`, `DIFFICULTIES`, `CUT_VECTORS`; `Timing(bpm: float, changes: list[BpmEvent])` with `.to_seconds(beat) -> float`, `.to_beats(seconds) -> float`.

- [ ] **Step 1: Write the failing test**

```python
from hypothesis import given, strategies as st
from saber_tooth.model import BpmEvent
from saber_tooth.timing import Timing


def test_constant_bpm():
    t = Timing(120.0, [])
    assert t.to_seconds(4.0) == 2.0
    assert t.to_beats(2.0) == 4.0


def test_timing_with_bpm_change():
    t = Timing(120.0, [BpmEvent(beat=4.0, bpm=60.0)])
    assert t.to_seconds(4.0) == 2.0
    assert t.to_seconds(5.0) == 3.0
    assert t.to_beats(3.0) == 5.0


@given(st.floats(min_value=0, max_value=2000), st.floats(min_value=40, max_value=400))
def test_round_trip(beat, bpm):
    t = Timing(bpm, [BpmEvent(beat=16.0, bpm=bpm * 1.5)])
    assert abs(t.to_beats(t.to_seconds(beat)) - beat) < 1e-6
```

- [ ] **Step 2:** Run `uv run pytest tests/test_timing.py -v`. Expected: FAIL, `ModuleNotFoundError`.
- [ ] **Step 3: Implement**

```python
# model.py
from dataclasses import dataclass, field
from enum import IntEnum

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
    raw: dict[str, list] = field(default_factory=dict)
    filename: str = ""


@dataclass(frozen=True)
class ColorScheme:
    id: str
    colors: dict[
        str, dict[str, float]
    ]  # saberAColor, saberBColor, environmentColor0, ... -> {r,g,b,a}


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
```

```python
# timing.py
from saber_tooth.model import BpmEvent


class Timing:
    """Beat <-> seconds conversion with piecewise-constant tempo."""

    def __init__(self, bpm: float, changes: list[BpmEvent]):
        segs = [BpmEvent(0.0, bpm)] + sorted(c for c in changes if c.beat > 0)
        self._segs: list[tuple[float, float, float]] = []  # (start_beat, start_s, bpm)
        start_s = 0.0
        for i, seg in enumerate(segs):
            if i:
                prev_beat, prev_s, prev_bpm = self._segs[-1]
                start_s = prev_s + (seg.beat - prev_beat) * 60.0 / prev_bpm
            self._segs.append((seg.beat, start_s, seg.bpm))

    def to_seconds(self, beat: float) -> float:
        b0, s0, bpm = next(s for s in reversed(self._segs) if s[0] <= beat or s is self._segs[0])
        return s0 + (beat - b0) * 60.0 / bpm

    def to_beats(self, seconds: float) -> float:
        b0, s0, bpm = next(s for s in reversed(self._segs) if s[1] <= seconds or s is self._segs[0])
        return b0 + (seconds - s0) * bpm / 60.0
```

- [ ] **Step 4:** Run `uv run pytest tests/test_timing.py -v`. Expected: 3 passed.
- [ ] **Step 5:** Commit `feat: add core map model and tempo timing` with paths `src/saber_tooth/model.py src/saber_tooth/timing.py tests/test_timing.py`.
