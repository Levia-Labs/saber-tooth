from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.crop.suggest import COUNT, TOLERANCE_S, suggest_crops

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
        assert 0.0 <= p.score <= 1.0
