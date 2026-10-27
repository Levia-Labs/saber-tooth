from itertools import pairwise

from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.checks import check_difficulty
from saber_tooth.generator import generate_all
from saber_tooth.generator.candidates import BarStats
from saber_tooth.generator.walls import place_walls
from saber_tooth.model import DIFFICULTIES, Color, Cut, Note
from saber_tooth.profiles import PROFILES
from tests.test_generator import realistic, synth


def calm_passage(bpm=140, seconds=120):
    """Realistic song with a thin, quiet stretch in the middle."""
    a = realistic(bpm, seconds)
    lo, hi = seconds / 6, seconds / 3
    a.kick[:] = [t for t in a.kick if not lo < t < hi]
    a.snare[:] = [t for t in a.snare if not lo < t < hi]
    a.hh[:] = [t for t in a.hh if not lo < t < hi or int(t * 10) % 7 == 0]
    return a


def test_walls_only_on_hard_and_above():
    _, diffs = generate_all(calm_passage(), 3)
    assert diffs["Easy"].walls == [] and diffs["Normal"].walls == []
    for name in ("Hard", "Expert", "ExpertPlus"):
        assert diffs[name].walls, name


def test_walls_never_overlap_notes_and_maps_stay_clean():
    for bpm in (100, 140, 170):
        a = calm_passage(bpm)
        timing, diffs = generate_all(a, 5)
        for name, d in diffs.items():
            assert check_difficulty(d, timing, PROFILES[name], a) == [], (bpm, name)
            for w in d.walls:
                for n in d.notes:
                    inside = w.x <= n.x < w.x + w.width and w.y <= n.y < w.y + w.height
                    assert not (inside and w.beat <= n.beat <= w.beat + w.duration)


def test_wall_shapes_and_density_caps():
    _, diffs = generate_all(calm_passage(), 3)
    for name, d in diffs.items():
        for w in d.walls:
            side = w.x in (0, 3) and w.y == 0 and (w.width, w.height) == (1, 5)
            crouch = (w.x, w.y, w.width, w.height) == (1, 2, 2, 3)
            assert side or (crouch and name == "ExpertPlus"), (name, w)
            assert 1 <= w.duration <= 4
        for a, b in pairwise(d.walls):
            assert b.beat >= a.beat + a.duration
    hard = diffs["Hard"].walls
    assert all(b.beat - a.beat >= 8 for a, b in pairwise(hard))


def test_walls_are_deterministic_per_seed():
    a = calm_passage()
    _, one = generate_all(a, 9)
    _, two = generate_all(a, 9)
    assert all(one[n].walls == two[n].walls for n in DIFFICULTIES)


def test_uniform_song_gets_sparse_phrase_boundary_walls():
    a = realistic(140)
    timing, diffs = generate_all(a, 1)
    assert diffs["Easy"].walls == [] and diffs["Normal"].walls == []
    for name in ("Hard", "Expert", "ExpertPlus"):
        d = diffs[name]
        assert d.walls, name
        assert check_difficulty(d, timing, PROFILES[name], a) == []
        for w in d.walls:
            assert w.x in (0, 3) and w.duration <= 2 and w.beat % 32 < 4
        assert all(b.beat - a_.beat >= 24 for a_, b in pairwise(d.walls))


def test_crouch_wall_needs_a_build_up_and_empty_lanes():
    energy = {b: 0.2 + 0.2 * b for b in range(5)}  # steady rise: build-up from bar 3
    stats = BarStats(energy=energy)
    crouches = set()
    for seed in range(20):
        for w in place_walls([], stats, 0.0, PROFILES["ExpertPlus"], seed):
            if w.y == 2:
                crouches.add(w.beat)
    assert crouches and crouches <= {12.0, 16.0}
    busy = [Note(12.5, 1, 1, Color.RED, Cut.DOWN)]
    for seed in range(20):
        walls = place_walls(busy, stats, 0.0, PROFILES["ExpertPlus"], seed)
        assert all(w.y != 2 or w.beat + w.duration < 12.5 or w.beat > 12.5 for w in walls)


@settings(max_examples=15, deadline=None)
@given(st.floats(80, 190), st.integers(40, 120), st.integers(0, 500))
def test_calm_songs_have_zero_findings_with_walls(bpm, seconds, seed):
    a = calm_passage(bpm, seconds)
    timing, diffs = generate_all(a, seed)
    for name, d in diffs.items():
        assert check_difficulty(d, timing, PROFILES[name], a) == []


def test_synth_song_still_clean():
    a = synth(120, 60, 0.1)
    timing, diffs = generate_all(a, 2)
    assert all(check_difficulty(d, timing, PROFILES[n], a) == [] for n, d in diffs.items())
