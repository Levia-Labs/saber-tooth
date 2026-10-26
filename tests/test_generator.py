import itertools
import time
from collections import Counter

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.analysis import Analysis
from saber_tooth.checks import check_difficulty
from saber_tooth.generator import (
    generate_all,
    generate_all_with_stats,
    generate_difficulty,
    tempo_map,
)
from saber_tooth.generator.motifs import BLUE_MOTIFS, RED_MOTIFS
from saber_tooth.model import CUT_VECTORS, DIFFICULTIES, BpmEvent, Color, Cut, Difficulty
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


def realistic(bpm=140, seconds=120):
    """Kick/snare on alternating quarters with 16th hi-hats."""
    spb = 60.0 / bpm
    beats = [i * spb for i in range(int(seconds / spb))]
    hh = [b + k * spb / 4 for b in beats for k in range(4)]
    return Analysis("r", "A minor", bpm, beats, beats[::2], beats[1::2], hh, None)


@pytest.mark.parametrize("bpm", [100, 140, 170])
def test_flow_variety_across_tempos_and_seeds(bpm):
    a = realistic(bpm)
    for seed in range(8):
        timing, diffs, stats = generate_all_with_stats(a, seed)
        for name in ("Expert", "ExpertPlus"):
            notes = diffs[name].notes
            where = (bpm, seed, name)
            cells = Counter((n.color, n.x, n.y) for n in notes)
            cuts = Counter(n.cut for n in notes)
            assert max(cells.values()) / len(notes) <= 0.30, where
            assert (cuts[Cut.UP] + cuts[Cut.DOWN]) / len(notes) < 0.55, where
            assert sum(1 for n in notes if n.y == 2) / len(notes) >= 0.10, where
            for hand in Color:
                assert len({(n.x, n.y) for n in notes if n.color == hand}) >= 5, where
            assert check_difficulty(diffs[name], timing, PROFILES[name], a) == []
        for name, stat in stats.items():
            assert stat.dropped < 0.05 * stat.selected, (bpm, seed, name)
            assert stat.final == len(diffs[name].notes)


def test_window_planning_has_no_burst_at_first_bar():
    a = realistic(140, 120)
    timing, _ = generate_all(a, 1)
    phase = timing.to_beats(a.beats[0])
    lo_s = timing.to_seconds(phase + 40.0)
    hi_s = timing.to_seconds(phase + 120.0)
    for name in ("Hard", "Expert", "ExpertPlus"):
        profile = PROFILES[name]
        d = generate_difficulty(a, timing, profile, 1, window=(lo_s, hi_s))
        first = [n for n in d.notes if n.beat < phase + 44.0]
        target = profile.target_nps * (timing.to_seconds(phase + 44.0) - lo_s)
        assert len(first) <= 1.2 * target + 1, (name, len(first), target)
        assert len(d.notes) >= 0.8 * profile.target_nps * (hi_s - lo_s)


def active_seconds(a, timing):
    from saber_tooth.generator.candidates import bar_stats, phase_of

    phase = phase_of(a, timing)
    return bar_stats(a, timing, phase, range(0, int(len(a.beats) / 4))).active_seconds()


@pytest.mark.parametrize("bpm", [100, 140, 170])
def test_tier_counts_follow_targets_and_separate(bpm):
    for a in (realistic(bpm), synth(bpm, 120, 0.0)):
        for seed in (5, 6, 7):
            timing, diffs = generate_all(a, seed)
            active = active_seconds(a, timing)
            counts = [len(diffs[n].notes) for n in DIFFICULTIES]
            for name, count in zip(DIFFICULTIES, counts, strict=True):
                target = PROFILES[name].target_nps * active
                assert 0.8 * target <= count <= 1.2 * target, (bpm, name, count, target)
            assert counts == sorted(set(counts))
            assert counts[4] >= 1.15 * counts[3] and counts[3] >= 1.15 * counts[2]


def test_silent_bars_get_no_filler_notes():
    a = realistic(140, 60)
    a.kick[:] = [t for t in a.kick if not 20 < t < 40]
    a.snare[:] = [t for t in a.snare if not 20 < t < 40]
    a.hh[:] = [t for t in a.hh if not 20 < t < 40]
    timing, diffs = generate_all(a, 2)
    for name, d in diffs.items():
        inside = [n for n in d.notes if 22 < timing.to_seconds(n.beat) < 38]
        assert inside == [], name


def test_window_fill_with_entry_and_exit_is_seamless():
    a = realistic(140, 60)
    lo, hi = 20.0, 30.0
    for seed in range(20):
        timing, diffs = generate_all(a, seed)
        for name in ("Hard", "ExpertPlus") if seed % 2 else ("Normal", "Expert"):
            d, profile = diffs[name], PROFILES[name]
            secs = [timing.to_seconds(n.beat) for n in d.notes]
            before = [n for n, s in zip(d.notes, secs, strict=True) if s < lo]
            after = [n for n, s in zip(d.notes, secs, strict=True) if s >= hi]
            entry = {h: sw[-1] for h, sw in build_swings(before, timing).items() if sw}
            exit_ = {h: sw[0] for h, sw in build_swings(after, timing).items() if sw}
            fill = generate_difficulty(
                a, timing, profile, seed, window=(lo, hi), entry=entry, exit=exit_
            )
            assert fill.notes and fill.bpm_events == d.bpm_events
            assert all(lo <= timing.to_seconds(n.beat) < hi for n in fill.notes)
            merged = Difficulty(name, d.njs, d.offset, notes=sorted(before + fill.notes + after))
            assert check_difficulty(merged, timing, profile, a) == [], (seed, name)


def test_empty_analysis_and_speed():
    empty = Analysis("s", "A", 120, [], [], [], [], None)
    _, diffs = generate_all(empty, 0)
    assert all(d.notes == [] for d in diffs.values())
    a = synth(150, 180, 0.2)
    start = time.perf_counter()
    generate_all(a, 9)
    assert time.perf_counter() - start < 5.0


def test_tempo_map_steady_tracker_with_jitter_stays_aligned():
    import random

    rng = random.Random(4)  # noqa: S311
    t, beats = 0.31, []
    for _ in range(400):
        beats.append(t)
        t += 0.5 * 1.003 + rng.uniform(-0.002, 0.002)
    beats[1] = beats[0] + 0.4985
    a = Analysis("s", "A", 120, beats, [], [], [], None)
    bpm, events = tempo_map(a)
    timing = Timing(bpm, events)
    phase = beats[0] * bpm / 60.0
    errors = [abs(timing.to_seconds(phase + k) - b) for k, b in enumerate(beats)]
    assert max(errors) <= 0.010


def test_tempo_map_base_ignores_first_interval_noise():
    beats = [0.0, 0.47] + [0.47 + 0.5 * i for i in range(1, 60)]
    bpm, _events = tempo_map(Analysis("s", "A", 120, beats, [], [], [], None))
    assert abs(bpm - 120) < 1.0


def test_timing_events_keep_the_beat_zero_override():
    from saber_tooth.generator.build import timing_events

    timing = Timing(100.0, [BpmEvent(0.0, 120.0), BpmEvent(16.0, 140.0)])
    rebuilt = Timing(100.0, timing_events(timing))
    assert timing.to_seconds(8) == pytest.approx(4.0)
    assert rebuilt.to_seconds(8) == pytest.approx(4.0)
    assert timing_events(Timing(100.0, [BpmEvent(16.0, 140.0)])) == [BpmEvent(16.0, 140.0)]
