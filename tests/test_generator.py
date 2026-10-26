import itertools
import time

from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.analysis import Analysis
from saber_tooth.checks import check_difficulty
from saber_tooth.generator import generate_all, generate_difficulty, tempo_map
from saber_tooth.generator.motifs import BLUE_MOTIFS, RED_MOTIFS
from saber_tooth.model import CUT_VECTORS, DIFFICULTIES, Color, Cut
from saber_tooth.profiles import PROFILES
from saber_tooth.swings import build_swings
from saber_tooth.timing import Timing


def synth(bpm, seconds, swing):
    spb = 60.0 / bpm
    beats = [i * spb for i in range(int(seconds / spb))]
    kick = beats[::2]
    snare = beats[1::2]
    hh = [b + spb / 2 * (1 + swing) for b in beats]
    return Analysis("s", "A minor", bpm, beats, kick, snare, hh, None)


@settings(max_examples=25, deadline=None)
@given(st.floats(70, 200), st.integers(30, 180), st.floats(0, 0.3), st.integers(0, 1000))
def test_generated_maps_have_zero_findings(bpm, seconds, swing, seed):
    a = synth(bpm, seconds, swing)
    timing, diffs = generate_all(a, seed)
    assert set(diffs) == set(DIFFICULTIES)
    for name, d in diffs.items():
        assert check_difficulty(d, timing, PROFILES[name], a) == []


def test_density_increases_with_difficulty():
    _timing, diffs = generate_all(synth(128, 120, 0.0), 7)
    counts = [len(diffs[n].notes) for n in DIFFICULTIES]
    assert counts == sorted(counts) and counts[0] < counts[-1]


def test_tempo_map_aligns_beats():
    a = synth(120, 30, 0.0)
    a.beats[:] = [0.3 + b for b in a.beats]
    bpm, events = tempo_map(a)
    t = Timing(bpm, events)
    assert abs(t.to_seconds(t.to_beats(a.beats[10])) - a.beats[10]) < 1e-6
    for k in (1, 10, 40):
        assert abs(t.to_beats(a.beats[k]) - t.to_beats(a.beats[0]) - k) < 1e-6


def test_tempo_map_follows_tempo_change():
    spb1, spb2 = 0.5, 0.4
    beats = [i * spb1 for i in range(20)]
    beats += [beats[-1] + (i + 1) * spb2 for i in range(20)]
    a = Analysis("s", "A", 120, beats, [], [], [], None)
    bpm, events = tempo_map(a)
    assert abs(bpm - 120) < 1e-9
    assert [round(e.bpm) for e in events] == [150]
    t = Timing(bpm, events)
    for k in (0, 19, 25, 39):
        assert abs(t.to_beats(beats[k]) - t.to_beats(beats[0]) - k) < 1e-6


def test_tempo_map_tolerates_jitter_and_short_input():
    a = synth(120, 30, 0.0)
    a.beats[5] += 0.001
    assert tempo_map(a)[1] == []
    short = Analysis("s", "A", 99, [0.0], [], [], [], None)
    assert tempo_map(short) == (99, [])


def test_deterministic_and_seed_sensitive():
    a = synth(140, 60, 0.1)
    _, one = generate_all(a, 3)
    _, two = generate_all(a, 3)
    _, other = generate_all(a, 4)
    assert all(one[n].notes == two[n].notes for n in DIFFICULTIES)
    assert any(one[n].notes != other[n].notes for n in DIFFICULTIES)


def test_motif_library_is_valid():
    assert len(RED_MOTIFS) >= 8
    for motifs, cols in ((RED_MOTIFS, (0, 1)), (BLUE_MOTIFS, (2, 3))):
        for m in motifs:
            assert len(m) == 4 and all(c != Cut.ANY and x in cols for c, x, _ in m)
            for (c1, _, _), (c2, _, _) in zip(m, m[1:] + m[:1], strict=True):
                u, v = CUT_VECTORS[c1], CUT_VECTORS[c2]
                assert u[0] * v[0] + u[1] * v[1] < 0


def test_flow_parity_hands_and_no_dots():
    a = synth(128, 90, 0.0)
    timing, diffs = generate_all(a, 11)
    for name, d in diffs.items():
        assert d.njs == PROFILES[name].njs and not d.bombs and not d.walls
        assert all(n.cut != Cut.ANY for n in d.notes)
        assert all((n.x <= 1) == (n.color == Color.RED) for n in d.notes)
        for swings in build_swings(d.notes, timing).values():
            for s, t in itertools.pairwise(swings):
                assert s.vector[0] * t.vector[0] + s.vector[1] * t.vector[1] < 0


def test_doubles_only_where_allowed():
    _timing, diffs = generate_all(synth(128, 60, 0.0), 1)

    def doubles(d):
        beats = [n.beat for n in d.notes if n.color == Color.RED]
        return len(beats) - len(set(beats) - {n.beat for n in d.notes if n.color == Color.BLUE})

    assert doubles(diffs["Easy"]) == 0 and doubles(diffs["Normal"]) == 0
    assert doubles(diffs["Expert"]) > 0


def test_window_limits_notes_and_uses_entry():
    a = synth(120, 60, 0.0)
    timing, _ = generate_all(a, 5)
    d = generate_difficulty(a, timing, PROFILES["Hard"], 5, window=(20.0, 30.0))
    assert d.notes
    assert all(20.0 <= timing.to_seconds(n.beat) < 30.0 for n in d.notes)


def test_empty_analysis_and_speed():
    empty = Analysis("s", "A", 120, [], [], [], [], None)
    _, diffs = generate_all(empty, 0)
    assert all(d.notes == [] for d in diffs.values())
    a = synth(150, 180, 0.2)
    start = time.perf_counter()
    generate_all(a, 9)
    assert time.perf_counter() - start < 5.0
