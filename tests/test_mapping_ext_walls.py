from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.checks import run_checks
from saber_tooth.fixer.me_strip import strip_precision_walls
from saber_tooth.mapio.mapping_ext import decode, encode, make_wall, v2_type_geometry
from saber_tooth.mapio.read_v2 import read_v2
from saber_tooth.mapio.read_v3 import read_v3
from saber_tooth.model import Beatmap, Color, Cut, Difficulty, MapInfo, Note, Wall


@given(st.integers(-999, 999))
def test_vanilla_values_decode_unchanged(v):
    assert decode(v) == v


@given(st.floats(-20, 20, allow_nan=False).filter(lambda v: abs(v) < 20))
def test_encode_decode_round_trip_within_tolerance(v):
    assert abs(decode(encode(v)) - v) <= 0.0005 + 1e-9


def test_documented_example_decodes_to_lanes():
    assert round(decode(-1408), 9) == -0.408
    assert round(decode(1563), 9) == 0.563
    assert round(decode(1005), 9) == 0.005


def test_vanilla_wall_stays_integer_and_unflagged():
    w = make_wall(1.0, 1, 0, 2.0, 2, 5)
    assert w == Wall(1.0, 1, 0, 2.0, 2, 5) and not w.me


def test_v3_reader_decodes_precision_walls():
    data = {"obstacles": [{"b": 4, "x": -1408, "y": 0, "d": 2, "w": 1563, "h": 5}]}
    (w,) = read_v3(data, "Easy", 10, 0, "f.dat").walls
    assert w.me and abs(w.x + 0.408) < 1e-9 and abs(w.width - 0.563) < 1e-9 and w.height == 5


def test_v2_reader_decodes_precision_walls():
    data = {
        "_obstacles": [{"_time": 1, "_lineIndex": 1500, "_type": 0, "_duration": 1, "_width": 1}]
    }
    (w,) = read_v2(data, "Easy", 10, 0, "f.dat").walls
    assert w.me and w.x == 0.5 and w.width == 1


def test_v2_precision_type_gives_precise_height():
    assert v2_type_geometry(1) == (2, 3) and v2_type_geometry(0) == (0, 5)
    assert v2_type_geometry(1000) == (0, 0)
    assert v2_type_geometry(2000) == (0, 5)
    assert v2_type_geometry(3000) == (0, 10)


def test_v2_type_boundary_4000_4001_and_readme_example():
    assert v2_type_geometry(4000) == (0, 15)
    assert v2_type_geometry(4001) == (0, 0)  # height 0, start 0
    y, h = v2_type_geometry(2304301)  # README: height 2300, start 300
    assert abs(h - 11.5) < 1e-9 and abs(y - 6.0) < 1e-9
    assert v2_type_geometry(5001) == (0, 0.005)  # height 1, start 0


def test_v2_precision_type_wall_is_flagged_and_stripped():
    data = {
        "_obstacles": [{"_time": 1, "_lineIndex": 1, "_type": 2000, "_duration": 1, "_width": 1}]
    }
    (w,) = read_v2(data, "Easy", 10, 0, "f.dat").walls
    assert w.me and (w.x, w.y, w.height) == (1, 0, 5)


def test_negative_precision_width_decodes_symmetrically():
    assert round(decode(-1500), 9) == -0.5


def _beatmap(walls):
    notes = [Note(5.0, 0, 1, Color.RED, Cut.DOWN), Note(5.0, 3, 1, Color.BLUE, Cut.DOWN)]
    d = Difficulty("Easy", 10, 0, notes=notes, walls=walls)
    info = MapInfo("s", "", "a", "m", 120, "s.ogg", "c.jpg", 0, 10, "DefaultEnvironment")
    return Beatmap(info, {"Easy": d})


def _rules(walls):
    return {f.rule for f in run_checks(_beatmap(walls), None)}


def test_precision_wall_outside_the_grid_never_counts():
    wall = make_wall(4.0, -2408, 0, 4.0, 1563, 5)  # lanes -1.408 .. -0.845
    assert wall.me and not ({"note-in-wall", "wall-trap", "wall-short"} & _rules([wall]))


def test_precision_wall_counts_only_for_the_cells_it_overlaps():
    wall = make_wall(4.0, 1000, 0, 4.0, 1800, 5)  # lane 0 .. 0.8: covers x=0, not x=3
    found = [f for f in run_checks(_beatmap([wall]), None) if f.rule == "note-in-wall"]
    assert [(f.notes[0].x) for f in found] == [0]


def test_vanilla_wall_still_flags_every_cell_it_covers():
    wall = Wall(4.0, 0, 0, 4.0, 4, 5)
    found = [f for f in run_checks(_beatmap([wall]), None) if f.rule == "note-in-wall"]
    assert sorted(f.notes[0].x for f in found) == [0, 3]


def test_strip_drops_precision_walls_and_keeps_vanilla():
    keep = Wall(1.0, 1, 0, 1.0, 1, 5)
    bm = _beatmap([keep, make_wall(2.0, 1500, 0, 1.0, 1, 5), make_wall(3.0, -1408, 0, 1, 1563, 5)])
    out = strip_precision_walls(bm)
    assert out.difficulties["Easy"].walls == [keep]
    assert len(bm.difficulties["Easy"].walls) == 3


def test_fix_beatmap_drops_precision_walls_and_flags_the_run():
    from saber_tooth.service.fixrun import fix_beatmap

    keep = Wall(1.0, 1, 0, 1.0, 1, 5)
    bm = _beatmap([keep, make_wall(2.0, 1500, 0, 1.0, 1, 5)])
    run = fix_beatmap(bm, None, None, 1)
    assert run.stripped and keep in run.fixed.difficulties["Easy"].walls
    assert not any(w.me for w in run.fixed.difficulties["Easy"].walls)


def test_strip_returns_same_map_when_vanilla():
    bm = _beatmap([Wall(1.0, 1, 0, 1.0, 1, 5)])
    assert strip_precision_walls(bm) is bm
