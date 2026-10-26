import json
from pathlib import Path

from saber_tooth.lightshow import Templates, Unit, learn

FIX = Path(__file__).parent / "fixtures" / "maps"


def test_learns_units_per_environment(tmp_path):
    t = learn(FIX)
    assert t.units and all(env != "DefaultEnvironment" for env in t.units)
    unit = next(iter(t.units.values()))[0]
    assert all(0 <= e.beat < 4 for e in unit.events)
    t.save(tmp_path / "t.json")
    assert Templates.load(tmp_path / "t.json").units.keys() == t.units.keys()


def test_units_rebased_stripped_and_roundtrip(tmp_path):
    t = learn(FIX)
    units = t.units["BTSEnvironment"]
    assert all(0.0 <= u.energy <= 1.0 for u in units)
    assert all(u.environment == "BTSEnvironment" for u in units)
    groups = [g for u in units for gs in u.groups.values() for g in gs]
    assert groups and all(0 <= g["b"] < 4 and "customData" not in g for g in groups)
    assert any(g["g"] == 0 for g in groups)
    assert t.schemes["BTSEnvironment"][0].id == "Custom"
    t.save(tmp_path / "t.json")
    again = Templates.load(tmp_path / "t.json")
    assert again.units == t.units and again.schemes == t.schemes
    assert isinstance(again.units["BTSEnvironment"][0], Unit)
    json.loads((tmp_path / "t.json").read_text(encoding="utf-8"))


def test_skips_broken_and_default_env(tmp_path):
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "Info.dat").write_text("{nope", encoding="utf-8")
    assert learn(tmp_path).units == {}


def test_custom_data_stripped(tmp_path):
    import shutil

    dst = tmp_path / "m"
    shutil.copytree(FIX / "v3_boxes", dst)
    f = dst / "Expert.dat"
    d = json.loads(f.read_text(encoding="utf-8"))
    d["lightColorEventBoxGroups"][0]["customData"] = {"x": 1}
    f.write_text(json.dumps(d), encoding="utf-8")
    t = learn(tmp_path)
    assert "customData" not in json.dumps([u.groups for u in t.units["BTSEnvironment"]])
