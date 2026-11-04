import re

from saber_tooth.environments import BY_NAME, CATALOGUE, COLOR_ROLES, format_catalogue
from saber_tooth.lightshow.units import BUNDLED, Templates


def test_catalogue_covers_every_learned_environment():
    learned = {e for e, u in Templates.load(BUNDLED).units.items() if u}
    assert learned == set(BY_NAME)
    assert len(CATALOGUE) == len(BY_NAME) == 20


def test_every_entry_is_complete():
    for e in CATALOGUE:
        assert e.moods and e.genres and e.setting
        assert all(0.0 <= v <= 1.0 for v in (e.valence, e.energy, e.intensity))
        assert set(e.palette) == set(COLOR_ROLES)
        assert all(re.fullmatch(r"#[0-9a-f]{6}", c) for c in e.palette.values())


def test_format_is_one_compact_line_per_environment():
    lines = format_catalogue().splitlines()
    assert len(lines) == len(CATALOGUE)
    assert lines == sorted(lines)
    assert all(line.count(" | ") == 5 for line in lines)
