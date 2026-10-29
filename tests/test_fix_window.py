"""Window verification and batching: same result as the whole-map path, no boundary findings."""

import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.checks import run_checks
from saber_tooth.fixer import window
from saber_tooth.fixer.verify import finding_key, new_findings
from saber_tooth.model import Color, Cut, Note
from saber_tooth.service import fixrun
from tests.test_fixer import _n, bm

note_st = st.builds(
    lambda i, x, y, c, cut: _n(8 + i * 0.125, x, y, Color(c), Cut(cut)),
    st.integers(0, 120),
    st.integers(0, 3),
    st.integers(0, 2),
    st.integers(0, 1),
    st.integers(0, 8),
)


def messy(count: int, seed: int = 1, step: float = 0.1) -> list[Note]:
    rng = random.Random(seed)  # noqa: S311  deterministic test data
    return [
        _n(8 + i * step, rng.randint(0, 3), rng.randint(0, 2), Color(i % 2), Cut(rng.randint(0, 8)))
        for i in range(count)
    ]


def _fix(m, windowed: bool, monkeypatch, batch: int | None = None):
    monkeypatch.setattr(window, "WINDOW_MIN_NOTES", 0 if windowed else 10**9)
    if batch:
        monkeypatch.setattr(window, "BATCH_NOTES", batch)
    return fixrun.fix_beatmap(m, None, None, 1, max_rounds=3)


def _state(run):
    return {n: (sorted(d.notes), sorted(d.walls)) for n, d in run.fixed.difficulties.items()}


@settings(max_examples=25, deadline=None)
@given(st.lists(note_st, min_size=2, max_size=45))
def test_windowed_fix_equals_the_whole_map_fix(notes):
    m = bm(notes)
    with pytest.MonkeyPatch.context() as mp:
        whole = _fix(m, False, mp)
        part = _fix(m, True, mp)
    assert _state(part) == _state(whole)
    assert len(part.steps) == len(whole.steps)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_windowed_fix_equals_whole_on_a_messy_map(seed, monkeypatch):
    m = bm(messy(90, seed))
    whole = _fix(m, False, monkeypatch)
    assert _state(_fix(m, True, monkeypatch)) == _state(whole)


def test_batches_cut_every_batch_notes_on_a_new_beat():
    d = bm(messy(500)).difficulties["Expert"]
    edges = window.batch_edges(d, 100)
    assert edges == sorted(set(edges)) and len(edges) == 4
    assert window.batch_of(edges, 0.0) == 0 and window.batch_of(edges, edges[1]) == 2
    assert window.batch_count(d, 100) == 5


@given(st.lists(note_st, min_size=0, max_size=60), st.integers(1, 30))
def test_every_beat_belongs_to_exactly_one_batch_in_order(notes, size):
    d = bm(notes).difficulties["Expert"]
    edges = window.batch_edges(d, size)
    ids = [window.batch_of(edges, n.beat) for n in sorted(d.notes)]
    assert ids == sorted(ids) and all(0 <= i <= len(edges) for i in ids)


def test_batched_fix_never_adds_a_finding_at_a_boundary(monkeypatch):
    m = bm(messy(260, 5, 0.12))
    before = run_checks(m)
    run = _fix(m, True, monkeypatch, batch=40)
    assert next(c for c in run.completed if c["difficulty"] == "Expert")["batches"] > 3
    after = run_checks(run.fixed)
    assert not new_findings(
        [f for f in after if f.rule != "missing-difficulty"],
        [f for f in before if f.rule != "missing-difficulty"],
    )
    assert {finding_key(f)[:2] for f in after if f.severity == "error"} <= {
        finding_key(f)[:2] for f in before
    }


def test_window_findings_match_the_whole_check_near_a_cut():
    m = bm(messy(300, 7))
    d = m.difficulties["Expert"]
    whole = run_checks(m, difficulty="Expert")
    lo, hi = d.notes[150].beat, d.notes[160].beat
    got = window.window_findings(m, "Expert", lo, hi, None)
    margin = 1.0  # beats at 120 bpm: inside the compared span the two agree exactly
    want = [f for f in whole if f.beat_start <= hi + margin and f.beat_end >= lo - margin]
    inner = {(f.rule, f.beat_start, f.beat_end) for f in got if lo <= f.beat_start <= hi}
    assert inner == {(f.rule, f.beat_start, f.beat_end) for f in want if lo <= f.beat_start <= hi}
