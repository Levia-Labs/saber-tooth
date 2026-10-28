import json

import pytest

from saber_tooth.crop.errors import InvalidWindow, NoNotes
from saber_tooth.crop.timeline import build_timeline, resolve_window, timeline_dict
from tests.crop_helpers import beatmap, stepped_map

DURATION = 143.0  # stepped_map(72) at 120 bpm: last note at beat 285


@pytest.fixture(scope="module")
def tl():
    return build_timeline(stepped_map(bars=72), DURATION, None)


def windows(tl, target):
    return [(w.start_beat, w.end_beat, w.end_kind) for w in tl.plans[target].suggestions]


def test_the_timeline_of_a_stepped_map(tl):
    # density steps give boundaries 0, 224 and the last bar line 284; see Task 4 for the scores
    assert tl.sections.boundaries == [0.0, 224.0, 284.0] and tl.sections.map_only is True
    assert tl.hardest == "ExpertPlus" and tl.drift_s is None
    assert windows(tl, 60) == [(0.0, 128.0, "phrase")]
    assert windows(tl, 120) == [(0.0, 224.0, "section")]
    assert set(tl.series) == {"Easy", "Normal", "Hard", "Expert", "ExpertPlus"}


def test_the_timeline_json_has_the_documented_shape(tl):
    data = json.loads(json.dumps(timeline_dict(tl, "abc")))
    assert data["map_id"] == "abc" and data["bpm"] == 120.0 and data["hardest"] == "ExpertPlus"
    assert set(data["lengths"]) == {"60", "120"} and data["grid_drift_s"] is None
    one = data["lengths"]["60"]
    assert one["enabled"] is True and one["band"] == [54.0, 66.0] and one["reason"] is None
    assert set(one["suggestions"][0]) == {
        "start_beat", "end_beat", "start_s", "end_s", "length_s", "end_kind", "score",
    }  # fmt: skip
    assert set(one["starts"][0]) == {"beat", "seconds", "ends"}
    assert set(one["starts"][0]["ends"][0]) == {"beat", "seconds", "kind"}
    assert set(data["sections"][0]) == {
        "start_beat", "end_beat", "start_s", "end_s", "nps", "intensity",
    }  # fmt: skip
    assert len(data["nps"]["Expert"]) == 143


def test_the_suggestion_resolves_to_its_own_points(tl):
    plan, start, end = resolve_window(tl, 0.0, 128.0)
    assert plan.target_s == 60 and (start.beat, end.beat, end.kind) == (0.0, 128.0, "phrase")
    plan, start, end = resolve_window(tl, 0.0, 224.0)
    assert plan.target_s == 120 and end.kind == "section"


@pytest.mark.parametrize(
    ("start", "end", "rule"),
    [
        (0.0, 0.0, "end_beat must be after start_beat"),
        (5.0, 133.0, "start_beat is not a section boundary"),
        (0.0, 64.0, "outside the bands 54-66 s and 108-132 s"),
        (0.0, 128.5, "end_beat is not an allowed end point"),
    ],
)
def test_resolve_window_names_the_broken_rule(tl, start, end, rule):
    with pytest.raises(InvalidWindow, match=rule):
        resolve_window(tl, start, end)


def test_a_song_too_short_for_any_length_refuses_every_window():
    short = build_timeline(stepped_map(bars=12), 20.0, None)
    assert not any(p.enabled for p in short.plans.values())
    with pytest.raises(InvalidWindow, match="no crop length"):
        resolve_window(short, 0.0, 128.0)


def test_a_map_without_notes_has_no_timeline():
    with pytest.raises(NoNotes):
        build_timeline(beatmap(), 100.0, None)
