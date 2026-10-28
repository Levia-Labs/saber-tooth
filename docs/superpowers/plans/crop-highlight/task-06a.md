# Task 6: Shift, trim, lead-in and light fades (pure)

**Files:**

- Create: `src/saber_tooth/crop/shift.py`
- Test: `tests/test_crop_shift.py`

**Interfaces:**

Consumes: `grid_events`, `tempo_at` (`crop/phrases.py`); `note_beats` (`crop/nps.py`); `BOX_KEYS` (`mapio/write.py`); `Beatmap`, `Difficulty`, `Wall`, `BasicEvent`, `BpmEvent`; `Timing`; `BAR`.

Produces (`saber_tooth.crop.shift`):

```python
LEAD_IN_S = 2.0
LIGHT_TYPES = (0, 1, 2, 3, 4)      # back lasers, ring lights, left lasers, right lasers, centre lights
FADE_LEVELS = (0.25, 0.5, 0.75, 1.0)
FADE_STEP_BEATS = 0.25

@dataclass(frozen=True)
class Cropped:
    beatmap: Beatmap        # shifted and trimmed; info.bpm is the tempo at the cut; info is otherwise the original's
    start_s: float          # where the cut starts in the original audio
    length_s: float         # seconds of the original audio kept
    lead_s: float           # seconds of silence put before them
    fade_out_s: float       # length of the last bar, for the audio fade-out

def crop_difficulty(d: Difficulty, start: float, end: float, lead_beats: float, bpm_events: list[BpmEvent]) -> Difficulty
def crop_beatmap(beatmap: Beatmap, timing: Timing, start_beat: float, end_beat: float) -> Cropped
```

`timing` is `grid_timing(beatmap)`. Rules: kept notes, bombs and events lie in `[start, end)`; new beat is `beat - start + lead_beats`; `lead_beats = ceil(lead seconds * tempo at start / 60)` where lead seconds make the earliest kept note of any difficulty land at 2 s or later; an arc (`sliders`) or chain (`burstSliders`) is kept only when its head `b` is at or after `start` and its tail `tb` is before `end`; walls overlapping the window are trimmed to it (a wall with zero or negative duration is kept only when its start lies inside); basic events: all five light types off at new beat 0, the state in force at the cut faded in over `FADE_LEVELS` from the lead-in end, and all five off at the new end beat; box groups starting inside are kept and a dark copy of the last kept `lightColorEventBoxGroups` group per group id is added at the new end beat.

- [ ] **Step 1: Write the failing test**

Create `tests/test_crop_shift.py`:

```python
from pathlib import Path

import pytest

from saber_tooth.crop.phrases import grid_timing
from saber_tooth.crop.shift import crop_beatmap
from saber_tooth.mapio import load_map, write_map
from saber_tooth.model import BasicEvent, Bomb, BpmEvent, Wall
from tests.crop_helpers import beatmap, diff

FIX = Path(__file__).parent / "fixtures" / "maps"
START, END = 32.0, 100.0


def crop(bm, start=START, end=END):
    return crop_beatmap(bm, grid_timing(bm), start, end)


def test_notes_and_bombs_shift_to_the_new_start():
    d = diff("Expert", [20.0, 40.0, 41.0, 99.5, 100.0])
    d.bombs = [Bomb(50.0, 1, 1), Bomb(120.0, 1, 1)]
    out = crop(beatmap(Expert=d))
    e = out.beatmap.difficulties["Expert"]
    assert [n.beat for n in e.notes] == [8.0, 9.0, 67.5]  # 100.0 is the first beat after the window
    assert [b.beat for b in e.bombs] == [18.0]
    assert out.lead_s == 0.0
    assert out.start_s == pytest.approx(16.0) and out.length_s == pytest.approx(34.0)
    assert out.fade_out_s == pytest.approx(2.0)


@pytest.mark.parametrize(
    ("first_beat", "new_beat", "lead_s"),
    [(32.0, 4.0, 2.0), (33.0, 4.0, 1.5), (40.0, 8.0, 0.0)],
)
def test_lead_in_puts_the_first_note_two_seconds_in(first_beat, new_beat, lead_s):
    out = crop(beatmap(Expert=diff("Expert", [first_beat, 50.0])))
    e = out.beatmap.difficulties["Expert"]
    assert out.lead_s == pytest.approx(lead_s)
    assert e.notes[0].beat == new_beat
    assert e.notes[0].beat * 60.0 / out.beatmap.info.bpm >= 2.0 - 1e-6


def test_lead_in_uses_the_earliest_note_of_any_difficulty():
    bm = beatmap(Easy=diff("Easy", [40.0]), Expert=diff("Expert", [33.0]))
    assert crop(bm).lead_s == pytest.approx(1.5)


def test_walls_are_trimmed_to_the_window():
    d = diff("Expert", [40.0])
    d.walls = [
        Wall(30.0, 1, 0, 6.0, 1, 5),
        Wall(98.0, 1, 0, 6.0, 1, 5),
        Wall(10.0, 1, 0, 2.0, 1, 5),
        Wall(50.0, 2, 0, 4.0, 1, 5),
    ]
    walls = crop(beatmap(Expert=d)).beatmap.difficulties["Expert"].walls
    assert [(w.beat, w.duration) for w in walls] == [(0.0, 4.0), (18.0, 4.0), (66.0, 2.0)]


def test_arcs_and_chains_that_cross_an_edge_are_dropped():
    d = diff("Expert", [40.0])
    arc = {"b": 40.0, "tb": 44.0, "x": 1, "y": 0, "c": 0, "d": 1, "tx": 2, "ty": 0, "tc": 1}
    chain = {"b": 50.0, "tb": 52.0, "x": 1, "y": 0, "c": 0, "d": 1, "tx": 2, "ty": 1, "sc": 4}
    d.raw = {
        "sliders": [arc, dict(arc, b=30.0, tb=40.0), dict(arc, b=98.0, tb=104.0)],
        "burstSliders": [chain, dict(chain, b=99.0, tb=101.0)],
    }
    raw = crop(beatmap(Expert=d)).beatmap.difficulties["Expert"].raw
    assert [(s["b"], s["tb"]) for s in raw["sliders"]] == [(8.0, 12.0)]
    assert [(s["b"], s["tb"]) for s in raw["burstSliders"]] == [(18.0, 20.0)]


def test_bpm_changes_inside_the_window_are_kept_and_retimed():
    events = [BpmEvent(20.0, 90.0), BpmEvent(60.0, 60.0), BpmEvent(120.0, 200.0)]
    out = crop(beatmap(Expert=diff("Expert", [40.0], bpm_events=events)))
    assert out.beatmap.info.bpm == 90.0  # the tempo in force at the cut
    assert out.beatmap.difficulties["Expert"].bpm_events == [BpmEvent(28.0, 60.0)]
    assert out.start_s == pytest.approx(18.0)
    assert out.length_s == pytest.approx(176.0 / 3)  # 28 beats at 90 bpm, then 40 beats at 60


def test_a_tempo_change_at_the_cut_becomes_the_base_tempo():
    out = crop(beatmap(Expert=diff("Expert", [40.0], bpm_events=[BpmEvent(32.0, 75.0)])))
    assert out.beatmap.info.bpm == 75.0
    assert out.beatmap.difficulties["Expert"].bpm_events == []


def test_lights_fade_in_and_black_out():
    d = diff("Expert", [40.0])
    d.events = [BasicEvent(30.0, 1, 5), BasicEvent(40.0, 1, 6), BasicEvent(60.0, 2, 5)]
    d.boosts = [(10.0, True)]
    e = crop(beatmap(Expert=d)).beatmap.difficulties["Expert"]
    off = [x for x in e.events if x.beat == 0.0 and x.value == 0]
    assert {x.type for x in off} == {0, 1, 2, 3, 4}
    ramp = [x for x in e.events if x.type == 1 and x.value == 5]
    steps = [(x.beat, x.float_value) for x in ramp]
    assert steps == [(0.0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.0)]
    end = [x for x in e.events if x.beat == 68.0]
    assert {x.type for x in end} == {0, 1, 2, 3, 4} and all(x.value == 0 for x in end)
    assert max(x.beat for x in e.events) == 68.0
    assert e.boosts == [(0.0, True), (68.0, False)]


def test_box_lights_are_kept_inside_and_blacked_out_at_the_end():
    group = {
        "b": 40.0,
        "g": 3,
        "e": [
            {
                "f": {"f": 1},
                "w": 0.0,
                "d": 1,
                "r": 0.0,
                "t": 0,
                "b": 0,
                "i": 0,
                "e": [
                    {"b": 0.0, "i": 0, "c": 1, "s": 1.0, "f": 0},
                    {"b": 1.0, "i": 1, "c": 0, "s": 0.5, "f": 1},
                ],
            }
        ],
    }
    d = diff("Expert", [40.0])
    d.raw = {"lightColorEventBoxGroups": [dict(group, b=10.0), group, dict(group, b=100.0)]}
    groups = crop(beatmap(Expert=d)).beatmap.difficulties["Expert"].raw["lightColorEventBoxGroups"]
    assert [g["b"] for g in groups] == [8.0, 68.0]
    assert groups[1]["e"][0]["e"] == [{"b": 0.0, "i": 0, "c": 1, "s": 0.0, "f": 0}]
    assert len(group["e"][0]["e"]) == 2  # the source is never mutated


def test_a_difficulty_with_no_notes_in_the_window_is_kept_empty():
    bm = beatmap(Easy=diff("Easy", [500.0]), Expert=diff("Expert", [40.0]))
    out = crop(bm)
    assert out.beatmap.difficulties["Easy"].notes == []


@pytest.mark.parametrize("name", ["v2_basic", "v2_bpm", "v3_boxes", "v4_audio_bpm", "v4_split"])
def test_every_map_version_crops_and_reads_back(name, tmp_path):
    bm = load_map(FIX / name)
    out = crop_beatmap(bm, grid_timing(bm), 0.0, 12.0)
    write_map(out.beatmap, tmp_path / "out", None)
    back = load_map(tmp_path / "out")
    assert set(back.difficulties) == set(bm.difficulties)
    assert back.info.bpm == out.beatmap.info.bpm
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest tests/test_crop_shift.py -q`
Expected: FAIL at collection with `ModuleNotFoundError: No module named 'saber_tooth.crop.shift'`.

Continued in [task-06b.md](task-06b.md).
