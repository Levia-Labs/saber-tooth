"""apply_ops keeps notes ordered by bisecting: same result as a list-and-sort reference."""

from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.fixer.fill_op import Fill
from saber_tooth.fixer.ops import Delete, Flip, Move, OpConflict, Recolor, apply_ops
from saber_tooth.mapio import load_map
from saber_tooth.model import Color, Cut, Note
from tests.test_checks_window import note_st
from tests.test_fixer import bm

EPS = 1e-6


def reference(notes, ops):
    out = list(notes)
    for op in ops:
        if isinstance(op, Fill):
            for n in op.notes:
                if any(abs(m.beat - n.beat) < EPS and (m.x, m.y) == (n.x, n.y) for m in out):
                    raise OpConflict("taken")
                out.append(n)
            continue
        if op.note not in out:
            raise OpConflict("missing")
        out.remove(op.note)
        if isinstance(op, Move):
            new = replace(op.note, x=op.x, y=op.y, cut=op.cut)
            if any(abs(m.beat - new.beat) < EPS and (m.x, m.y) == (new.x, new.y) for m in out):
                raise OpConflict("taken")
            out.append(new)
        elif isinstance(op, Flip):
            out.append(replace(op.note, cut=op.cut))
        elif isinstance(op, Recolor):
            out.append(replace(op.note, color=Color(1 - op.note.color)))
    return sorted(out)


def op_st(notes):
    pick = st.sampled_from(notes)
    stale = st.builds(lambda n: replace(n, x=(n.x + 1) % 4), pick)
    note = st.one_of(pick, pick, stale)
    cells = st.tuples(st.integers(0, 3), st.integers(0, 2), st.sampled_from(list(Cut)))
    return st.one_of(
        st.builds(lambda n, c: Move("Expert", n, *c), note, cells),
        st.builds(lambda n, c: Flip("Expert", n, c[2]), note, cells),
        st.builds(lambda n: Recolor("Expert", n), note),
        st.builds(lambda n: Delete("Expert", n), note),
        st.builds(
            lambda n, c: Fill("Expert", n.beat, n.beat, (Note(n.beat, *c[:2], Color.RED, c[2]),)),
            pick,
            cells,
        ),
    )


def check(notes, ops):
    m = bm(notes)
    before = list(m.difficulties["Expert"].notes)
    try:
        want = reference(sorted(notes), ops)
    except OpConflict:
        with pytest.raises(OpConflict):
            apply_ops(m, ops)
        return
    got = apply_ops(m, ops)
    assert got.difficulties["Expert"].notes == want
    assert m.difficulties["Expert"].notes == before


@settings(max_examples=80, deadline=None)
@given(st.data(), st.lists(note_st, min_size=2, max_size=60, unique=True))
def test_apply_ops_matches_the_reference(data, notes):
    ops = data.draw(st.lists(op_st(notes), min_size=1, max_size=4))
    check(notes, ops)


def test_unsorted_input_is_still_sorted_on_output():
    m = bm([Note(2, 0, 0, Color.RED, Cut.UP), Note(1, 1, 0, Color.BLUE, Cut.UP)])
    m.difficulties["Expert"].notes.reverse()
    n = m.difficulties["Expert"].notes[0]
    out = apply_ops(m, [Delete("Expert", n)])
    assert out.difficulties["Expert"].notes == [m.difficulties["Expert"].notes[1]]
    out = apply_ops(m, [Flip("Expert", n, Cut.DOWN)])
    assert out.difficulties["Expert"].notes == sorted(out.difficulties["Expert"].notes)


MAPS = Path(__file__).parent / "fixtures" / "maps"


@pytest.mark.parametrize("folder", sorted(p.name for p in MAPS.iterdir() if p.is_dir()))
def test_fixture_maps_apply_like_the_reference(folder):
    m = load_map(MAPS / folder)
    for name, d in m.difficulties.items():
        if len(d.notes) < 3:
            continue
        a, b = d.notes[0], d.notes[len(d.notes) // 2]
        ops = [Flip(name, a, Cut.UP), Recolor(name, b), Delete(name, d.notes[-1])]
        got = apply_ops(m, ops).difficulties[name].notes
        want = [replace(a, cut=Cut.UP), replace(b, color=Color(1 - b.color))]
        rest = [n for n in d.notes if n not in (a, b, d.notes[-1])]
        assert got == sorted(rest + want)
