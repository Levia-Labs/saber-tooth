import sqlite3

from saber_tooth.beatsaver.presets import OLD_SEEDED_NAME, SEEDED_NAME, Presets


def _old_db(path, extra=()):
    db = sqlite3.connect(path)
    db.executescript(
        "CREATE TABLE bs_presets(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE,"
        " filters TEXT, seeded INTEGER);"
        "CREATE TABLE bs_meta(key TEXT PRIMARY KEY, value TEXT);"
        "INSERT INTO bs_meta VALUES('seeded','1');"
    )
    db.execute(
        "INSERT INTO bs_presets(name, filters, seeded) VALUES(?, '{}', 1)", (OLD_SEEDED_NAME,)
    )
    for name in extra:
        db.execute("INSERT INTO bs_presets(name, filters, seeded) VALUES(?, '{}', 0)", (name,))
    db.commit()
    db.close()


def test_fresh_db_seeds_new_name(tmp_path):
    names = [p["name"] for p in Presets(tmp_path / "a.db").list()]
    assert names == [SEEDED_NAME] == ["Easy-to-Hard gems"]


def test_old_seeded_row_is_renamed(tmp_path):
    _old_db(tmp_path / "b.db")
    rows = Presets(tmp_path / "b.db").list()
    assert [(p["name"], p["seeded"]) for p in rows] == [(SEEDED_NAME, True)]


def test_user_preset_with_old_name_untouched(tmp_path):
    db = sqlite3.connect(tmp_path / "c.db")
    db.executescript(
        "CREATE TABLE bs_presets(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE,"
        " filters TEXT, seeded INTEGER);"
        "CREATE TABLE bs_meta(key TEXT PRIMARY KEY, value TEXT);"
        "INSERT INTO bs_meta VALUES('seeded','1');"
        "INSERT INTO bs_presets(name, filters, seeded) VALUES('Gentle full-spread hits','{}',0);"
    )
    db.commit()
    db.close()
    rows = Presets(tmp_path / "c.db").list()
    assert [(p["name"], p["seeded"]) for p in rows] == [(OLD_SEEDED_NAME, False)]
