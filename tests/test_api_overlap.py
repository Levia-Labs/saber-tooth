from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.api.overlap import conflicts_with
from saber_tooth.fixer import Fill, Move, Recolor
from saber_tooth.model import Color, Cut, Note

BEAT = 166.3175048828125
BLUE = Note(BEAT, 0, 0, Color.BLUE, Cut.DOWN)
RED_A = Note(BEAT, 1, 1, Color.RED, Cut.DOWN)
RED_B = Note(BEAT, 2, 1, Color.RED, Cut.DOWN)


def prop(pid, ops, status="approved", difficulty="Expert"):
    return {
        "id": pid,
        "status": status,
        "difficulty": difficulty,
        "ops": [o.to_dict() for o in ops],
    }


def test_user_case_31_and_32_overlap_on_the_shared_red_note():
    p31 = prop(31, [Recolor("Expert", RED_B), Recolor("Expert", BLUE)])
    p32 = prop(32, [Move("Expert", RED_A, 1, 1, Cut.DOWN), Move("Expert", RED_B, 1, 2, Cut.DOWN)])
    assert conflicts_with([p31, p32]) == {31: [32], 32: [31]}


def test_disjoint_notes_other_difficulties_and_closed_proposals_do_not_overlap():
    a = prop(1, [Recolor("Expert", RED_B)])
    other_note = prop(2, [Recolor("Expert", RED_A)])
    other_diff = prop(3, [Recolor("Hard", RED_B)])
    rejected = prop(4, [Recolor("Expert", RED_B)], status="rejected")
    superseded = prop(5, [Recolor("Expert", RED_B)], status="superseded")
    assert conflicts_with([a, other_note, other_diff, rejected, superseded]) == {}


def test_fill_range_overlaps_a_note_inside_it():
    fill = Fill("Expert", 160.0, 170.0, (), (), ())
    p = prop(1, [fill])
    inside = prop(2, [Recolor("Expert", RED_B)])
    outside = prop(3, [Recolor("Expert", Note(200.0, 0, 0, Color.RED, Cut.DOWN))])
    assert conflicts_with([p, inside, outside]) == {1: [2], 2: [1]}


def test_unreadable_ops_are_skipped():
    bad = {"id": 1, "status": "pending", "difficulty": "Expert", "ops": [{"op": "move"}, 5]}
    assert conflicts_with([bad]) == {}


@given(st.lists(st.tuples(st.integers(0, 3), st.integers(0, 3)), max_size=8))
def test_overlap_is_symmetric_and_irreflexive(cells):
    proposals = [
        prop(i, [Recolor("Expert", Note(4.0, x, y, Color.RED, Cut.DOWN))])
        for i, (x, y) in enumerate(cells)
    ]
    found = conflicts_with(proposals)
    for pid, ids in found.items():
        assert pid not in ids
        assert all(pid in found[other] for other in ids)
