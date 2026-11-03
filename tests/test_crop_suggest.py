from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.crop.suggest import COUNT, MIN_POINTS, POINTS, TOLERANCE_S, suggest_crops
from saber_tooth.crop.valley import cut_valley, prefix

BAR_S = 2.0


def _args(series, duration=None):
    duration = duration or float(len(series))
    bars = [i * 4.0 for i in range(int(duration / BAR_S) + 1)]
    return {
        "series": {"Expert": series},
        "hardest": "Expert",
        "bars": bars,
        "to_seconds": lambda b: b / 2.0,
        "boundaries": [b for b in bars[::8]],
        "duration_s": duration,
    }


def arc_song() -> list[float]:
    """300 s: calm, a rise 100-130, the peak 130-150, a release 150-180, calm again."""
    out = []
    for t in range(300):
        if t < 100 or t >= 190:
            out.append(2.0 if t % 5 else 1.0)
        elif t < 130:
            out.append(2.0 + (t - 100) / 6)
        elif t < 150:
            out.append(7.0)
        else:
            out.append(max(2.0, 7.0 - (t - 150) / 6))
    return out


def test_the_best_pick_holds_the_peak_with_build_up_and_release():
    best = suggest_crops(**_args(arc_song()))[0]
    assert best.start_s < 130 and best.end_s > 150
    assert best.start_s <= 125 and best.end_s >= 155
    assert "peak at 2:" in best.reason and best.reason.startswith("rise from ")


def test_picks_are_distinct_ranked_and_bounded():
    picks = suggest_crops(**_args(arc_song()))
    assert 1 <= len(picks) <= COUNT
    assert [p.score for p in picks] == sorted((p.score for p in picks), reverse=True)
    for i, a in enumerate(picks):
        for b in picks[i + 1 :]:
            shared = max(0.0, min(a.end_s, b.end_s) - max(a.start_s, b.start_s))
            assert shared / min(a.length_s, b.length_s) < 0.5


def test_a_short_song_has_no_candidate():
    assert suggest_crops(**_args([3.0] * 40)) == []


@settings(max_examples=25, deadline=None)
@given(st.lists(st.integers(0, 9), min_size=40, max_size=260).map(lambda v: [float(x) for x in v]))
def test_windows_are_snapped_in_tolerance_and_deterministic(series):
    args = _args(series)
    picks = suggest_crops(**args)
    assert picks == suggest_crops(**args)
    assert len(picks) <= COUNT
    bars = set(args["bars"])
    for p in picks:
        assert p.start_beat in bars and p.end_beat in bars
        assert abs(p.length_s - p.target_s) <= TOLERANCE_S[p.target_s] + 1e-6
        assert 0 <= p.start_s < p.end_s <= len(series) + 1e-6
        assert MIN_POINTS <= p.score <= 100.0


def test_points_total_100_and_the_breakdown_sums_to_the_score():
    assert sum(pts for _, pts in POINTS.values()) == 100.0
    picks = suggest_crops(**_args(arc_song()))
    assert picks
    for p in picks:
        assert [x.key for x in p.breakdown] == list(POINTS)
        assert all(0.0 <= x.points <= x.max_points for x in p.breakdown)
        assert abs(sum(x.points for x in p.breakdown) - p.score) < 1e-6


def test_nothing_below_the_point_floor_is_proposed():
    assert suggest_crops(**_args([2.0 if t % 3 else 0.0 for t in range(300)])) == []


def test_a_zero_note_valley_cut_beats_a_busy_cut():
    quiet = prefix([0.0] * 60)
    busy = prefix([4.0] * 60)
    assert cut_valley(quiet, [], 0.0, 30) == 1.0
    assert cut_valley(busy, [], 0.0, 30) < 0.1
    loud = prefix([9.0] * 60)
    assert cut_valley(quiet, loud, 9.0, 30) < cut_valley(quiet, prefix([0.0] * 60), 9.0, 30)


def _valley_song():
    """Notes everywhere except a silent gap at 90-100 s and 210-220 s, rising between."""
    return [
        0.0 if 90 <= t < 100 or 210 <= t < 220 else (5.0 if 130 <= t < 190 else 3.0)
        for t in range(300)
    ]


def test_cuts_land_in_valleys_when_one_is_in_reach():
    best = suggest_crops(**_args(_valley_song()))[0]
    series = _valley_song()
    for cut in (best.start_s, best.end_s):
        assert sum(series[max(0, int(cut) - 2) : int(cut) + 2]) <= 3.0


def test_audio_energy_pulls_cuts_to_quiet_audio():
    series = arc_song()
    plain = suggest_crops(**_args(series))[0]
    dip = int(plain.start_s) - 20  # a quiet stretch of audio 20 s before the plain start
    audio = [0.0 if dip - 4 <= t < dip + 4 else 9.0 for t in range(300)]
    best = suggest_crops(**_args(series), audio=audio)[0]
    assert abs(best.start_s - dip) < abs(plain.start_s - dip)
