from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.generator import generate_all
from saber_tooth.generator.connectors import CHAIN_BEATS, add_connectors, bar_energy
from saber_tooth.mapio.write import difficulty_json
from saber_tooth.model import CUT_VECTORS, Bomb, Color, Cut, Difficulty, Note, Wall
from saber_tooth.profiles import PROFILES
from saber_tooth.swings import angle_between
from saber_tooth.timing import Timing
from tests.test_generator import synth

TIMING = Timing(120.0, [])
EXPERT_PLUS = PROFILES["ExpertPlus"]


def diff(notes, name="ExpertPlus", **kw):
    return Difficulty(name, 18, 0, notes=sorted(notes), **kw)


def crowd(start):
    """A busy bar of blue dots on the far column, far from the pairs under test."""
    return [Note(start + i * 0.25, 3, 2, Color.BLUE, Cut.ANY) for i in range(16)]


def calm_pair():
    """Two reversing red hits two beats apart in a bar that is quiet next to the crowd."""
    return [
        Note(0.0, 1, 2, Color.RED, Cut.DOWN),
        Note(2.0, 1, 0, Color.RED, Cut.UP),
        *crowd(8.0),
    ]


def test_arc_links_a_flowing_pair_in_a_calm_bar():
    d = diff(calm_pair())
    arcs, _ = add_connectors(d, TIMING, EXPERT_PLUS)
    assert arcs == 1
    arc = d.raw["sliders"][0]
    assert (arc["b"], arc["tb"]) == (0.0, 2.0)
    assert arc["c"] == 0 and (arc["x"], arc["y"], arc["tx"], arc["ty"]) == (1, 2, 1, 0)
    assert set(arc) == {"b", "c", "x", "y", "d", "mu", "tb", "tx", "ty", "tc", "tmu", "m"}


def test_easy_has_no_connectors():
    d = diff(calm_pair(), "Easy")
    assert add_connectors(d, TIMING, PROFILES["Easy"]) == (0, 0)
    assert "sliders" not in d.raw and "burstSliders" not in d.raw


def test_density_scales_with_difficulty():
    pairs = [
        n
        for k in range(0, 40, 4)
        for n in (
            Note(k * 8.0, 1, 2, Color.RED, Cut.DOWN),
            Note(k * 8.0 + 2, 1, 0, Color.RED, Cut.UP),
        )
    ]
    pairs += [n for i in range(12) for n in crowd(400.0 + 4 * i)]
    normal = add_connectors(diff(pairs, "Normal"), TIMING, PROFILES["Normal"])[0]
    top = add_connectors(diff(pairs), TIMING, EXPERT_PLUS)[0]
    assert 0 < normal < top


def test_wall_in_the_span_blocks_the_arc():
    d = diff(calm_pair(), walls=[Wall(0.5, 0, 0, 1.0, 1, 3)])
    assert add_connectors(d, TIMING, EXPERT_PLUS)[0] == 0


def test_bomb_in_the_span_blocks_the_arc():
    d = diff(calm_pair(), bombs=[Bomb(1.0, 0, 0)])
    assert add_connectors(d, TIMING, EXPERT_PLUS)[0] == 0


def test_other_hand_note_in_the_arc_box_blocks_it():
    d = diff([*calm_pair(), Note(1.0, 1, 1, Color.BLUE, Cut.DOWN)])
    assert add_connectors(d, TIMING, EXPERT_PLUS)[0] == 0


def test_same_direction_pair_is_not_an_arc():
    notes = [
        Note(0.0, 1, 2, Color.RED, Cut.DOWN),
        Note(2.0, 1, 0, Color.RED, Cut.DOWN),
        *crowd(8.0),
    ]
    assert add_connectors(diff(notes), TIMING, EXPERT_PLUS)[0] == 0


def test_chain_extends_an_accented_hit_in_a_busy_bar():
    notes = [Note(8.0, 0, 0, Color.RED, Cut.UP_RIGHT), *crowd(8.25)[:-1]]
    d = diff(notes)
    _, chains = add_connectors(d, TIMING, EXPERT_PLUS)
    assert chains == 1
    chain = d.raw["burstSliders"][0]
    assert (chain["b"], chain["tb"]) == (8.0, 8.0 + CHAIN_BEATS)
    assert (chain["tx"], chain["ty"]) == (2, 2) and chain["sc"] == 4 and chain["d"] == 5
    assert set(chain) == {"b", "c", "x", "y", "d", "tb", "tx", "ty", "sc", "s"}


def test_energy_is_normalised():
    e = bar_energy([Note(b, 0, 0, Color.RED, Cut.ANY) for b in (0, 4, 4.5, 5, 5.5)])
    assert e == [0.25, 1.0]


def _box(head, s):
    return (
        (min(head.x, s["tx"]), max(head.x, s["tx"])),
        (min(head.y, s["ty"]), max(head.y, s["ty"])),
    )


@settings(max_examples=12, deadline=None)
@given(st.floats(70, 200), st.integers(30, 120), st.integers(0, 500))
def test_generated_connectors_are_clear_and_valid(bpm, seconds, seed):
    _timing, diffs = generate_all(synth(bpm, seconds, 0.0), seed)
    assert not diffs["Easy"].raw.get("sliders") and not diffs["Easy"].raw.get("burstSliders")
    for d in diffs.values():
        notes = {(n.beat, n.x, n.y, int(n.color)): n for n in d.notes}
        for key in ("sliders", "burstSliders"):
            for s in d.raw.get(key, []):
                head = notes[(s["b"], s["x"], s["y"], s["c"])]
                assert head.cut != Cut.ANY and s["d"] == int(head.cut) and s["tb"] > s["b"]
                if key == "sliders":
                    tail = notes[(s["tb"], s["tx"], s["ty"], s["c"])]
                    assert angle_between(CUT_VECTORS[head.cut], CUT_VECTORS[tail.cut]) >= 135
                    own = {head, tail}
                else:
                    assert 0 <= s["tx"] < 4 and 0 <= s["ty"] < 3 and s["sc"] >= 3
                    own = {head}
                (x0, x1), (y0, y1) = _box(head, s)
                inside = [
                    n
                    for n in d.notes
                    if s["b"] <= n.beat <= s["tb"] and n not in own
                    and x0 <= n.x <= x1 and y0 <= n.y <= y1
                ]  # fmt: skip
                assert not inside
                assert not [w for w in d.walls if w.beat < s["tb"] and w.beat + w.duration > s["b"]]
        difficulty_json(d)  # serialises as v3


def test_generation_adds_connectors_on_higher_tiers():
    _t, diffs = generate_all(synth(128, 150, 0.0), 3)
    total = {
        n: len(d.raw.get("sliders", [])) + len(d.raw.get("burstSliders", []))
        for n, d in diffs.items()
    }
    assert total["Easy"] == 0
    assert sum(total.values()) > 0
