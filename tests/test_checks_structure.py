import json

from saber_tooth.checks import RULES, check_difficulty, run_checks
from saber_tooth.model import (
    DIFFICULTIES,
    BasicEvent,
    Beatmap,
    Color,
    Cut,
    Difficulty,
    MapInfo,
    Note,
)
from saber_tooth.profiles import PROFILES
from saber_tooth.timing import Timing


def make_map(env="NiceEnvironment", names=DIFFICULTIES, lit=True) -> Beatmap:
    info = MapInfo("s", "", "a", "m", 120.0, "song.ogg", "c.png", 0, 10, env)
    diffs = {n: Difficulty(n, 16, 0) for n in names}
    if lit:
        for d in diffs.values():
            d.events.append(BasicEvent(0.0, 0, 1))
    return Beatmap(info, diffs)


def test_complete_map_has_no_map_findings():
    assert run_checks(make_map()) == []


def test_missing_difficulty_is_error():
    fs = run_checks(make_map(names=DIFFICULTIES[:4]))
    got = [(f.rule, f.difficulty, f.severity) for f in fs]
    assert got == [("missing-difficulty", "ExpertPlus", "error")]


def test_default_environment_is_warn():
    fs = run_checks(make_map(env="DefaultEnvironment"))
    got = [(f.rule, f.difficulty, f.severity) for f in fs]
    assert got == [("default-environment", "*", "warn")]


def test_unlit_map_is_warn():
    fs = run_checks(make_map(lit=False))
    assert [(f.rule, f.severity) for f in fs] == [("default-environment", "warn")]


def test_box_groups_count_as_lighting():
    bm = make_map(lit=False)
    bm.difficulties["Expert"].raw["lightColorEventBoxGroups"] = [{"b": 0}]
    assert run_checks(bm) == []


def test_rules_filter_applies_to_map_rules():
    bm = make_map(env="DefaultEnvironment", names=DIFFICULTIES[:4])
    assert [f.rule for f in run_checks(bm, rules={"missing-difficulty"})] == ["missing-difficulty"]


def test_difficulty_filter_and_sorting():
    bm = make_map()
    bm.difficulties["Expert"].notes = sorted(
        [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(4.5, 1, 0, Color.RED, Cut.DOWN)]
    )
    bm.difficulties["Easy"].notes = list(bm.difficulties["Expert"].notes)
    fs = run_checks(bm)
    assert [f.difficulty for f in fs] == sorted(f.difficulty for f in fs)
    only = run_checks(bm, difficulty="Expert")
    assert only and {f.difficulty for f in only} == {"Expert"}
    assert run_checks(bm) == run_checks(bm)


def test_finding_to_dict_is_json_safe():
    d = Difficulty("Expert", 16, 0, notes=[Note(4.0, 1, 0, Color.RED, Cut.DOWN)] * 2)
    d.notes = [Note(4.0, 1, 0, Color.RED, Cut.DOWN), Note(4.5, 1, 0, Color.RED, Cut.DOWN)]
    fs = check_difficulty(d, Timing(120.0, []), PROFILES["Expert"])
    assert fs and isinstance(json.loads(json.dumps(fs[0].to_dict()))["notes"][0], dict)


def test_registry_is_extensible_and_receives_analysis():
    seen = []
    RULES["probe"] = lambda d, sw, t, p, analysis=None: seen.append(analysis) or []
    try:
        d = Difficulty("Expert", 16, 0)
        check_difficulty(d, Timing(120.0, []), PROFILES["Expert"], analysis="A")
        assert seen == ["A"]
    finally:
        del RULES["probe"]


def test_difficulty_filter_skips_map_rules_unless_named():
    bm = make_map(names=("Expert",))
    assert run_checks(bm, difficulty="Expert") == []
    named = run_checks(bm, difficulty="Expert", rules={"missing-difficulty"})
    assert len(named) == 4
