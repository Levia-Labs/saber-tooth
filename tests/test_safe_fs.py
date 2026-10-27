import pytest

from saber_tooth.safe_fs import LevelsWriter, WriteRefused, windows_safe_component


def test_refuses_write_into_existing_map(tmp_path):
    (tmp_path / "abc (Song - X)").mkdir()
    w = LevelsWriter(tmp_path)
    with pytest.raises(WriteRefused):
        w.guard(tmp_path / "abc (Song - X)" / "Info.dat")


def test_commit_and_unique_name(tmp_path):
    (tmp_path / "m [saber-tooth]").mkdir()
    w = LevelsWriter(tmp_path)
    assert w.unique_name("m [saber-tooth]") == "m [saber-tooth 2]"
    p = w.new_folder("n")
    (p / "Info.dat").write_text("{}", encoding="utf-8")
    final = w.commit(p, "n")
    assert final.is_dir() and not p.exists()


def test_commit_refuses_existing(tmp_path):
    (tmp_path / "n").mkdir()
    w = LevelsWriter(tmp_path)
    p = w.new_folder("n2")
    with pytest.raises(WriteRefused):
        w.commit(p, "n")


def test_stale_partial_does_not_block(tmp_path):
    (tmp_path / ".n.partial").mkdir()
    (tmp_path / ".n.partial" / "old.dat").write_text("x", encoding="utf-8")
    w = LevelsWriter(tmp_path)
    p = w.new_folder("n")
    assert p.is_dir() and not (p / "old.dat").exists()


@pytest.mark.parametrize(
    "name",
    ["a:b", "a:stream", "x\x01y", "a<b", "a>b", 'a"b', "a|b", "a?b", "a*b", "a.", "a ", "", "..",
     "CON", "con", "Nul.txt", "aux.tar.gz", "COM1", "lpt9.dat", "prn ", "a/b", "a\b"],
)  # fmt: skip
def test_windows_unsafe_components_rejected(name):
    assert not windows_safe_component(name)


@pytest.mark.parametrize(
    "name", ["Info.dat", "song.ogg", "CONSOLE", "COM10", "a b", "3a1f4 (S - M)"]
)
def test_windows_safe_components_accepted(name):
    assert windows_safe_component(name)


def test_new_folder_refuses_reserved_name(tmp_path):
    w = LevelsWriter(tmp_path)
    with pytest.raises(WriteRefused):
        w.new_folder("NUL")
    with pytest.raises(WriteRefused):
        w.commit(tmp_path, "a:b")
