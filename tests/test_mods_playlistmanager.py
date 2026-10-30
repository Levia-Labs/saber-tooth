"""PlaylistManager status and install over a fake BeatMods and a temporary game folder."""

import hashlib
import io
import zipfile

import pytest

from saber_tooth.mods.beatmods import BeatModsError, ModBuild
from saber_tooth.mods.playlistmanager import GITHUB, PlaylistManagerMod
from saber_tooth.settings import Settings


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()  # noqa: S324 - BeatMods publishes MD5


def zipped(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


FILES = {
    "BSIPA": {"IPA/Data/Managed/IPA.Injector.dll": b"ipa"},
    "SongCore": {"Plugins/SongCore.dll": b"sc"},
    "BeatSaberPlaylistsLib": {"Libs/BeatSaberPlaylistsLib.dll": b"lib"},
    "PlaylistManager": {"Plugins/PlaylistManager.dll": b"pm"},
}


def builds() -> list[ModBuild]:
    ids = {"BSIPA": 1, "SongCore": 2, "BeatSaberPlaylistsLib": 3, "PlaylistManager": 4}
    out = []
    for name, files in FILES.items():
        deps = {"PlaylistManager": (2, 3), "SongCore": (1,), "BeatSaberPlaylistsLib": (2,)}.get(
            name, ()
        )
        out.append(
            ModBuild(
                ids[name],
                ids[name],
                name,
                "1.7.3",
                md5(zipped(files)),
                f"https://github.com/x/{name}",
                {p: md5(d) for p, d in files.items()},
                deps,
                9,
            )
        )
    return out


class FakeMods:
    def __init__(self, supported=True, fail=None):
        self.supported, self.fail, self.downloads, self.versions = supported, fail, [], []

    def mods(self, game_version=None):
        if self.fail:
            raise BeatModsError(self.fail)
        self.versions.append(game_version)
        return builds() if (game_version is None or self.supported) else []

    def download(self, build):
        self.downloads.append(build.name)
        return zipped(FILES[build.name])


@pytest.fixture
def game(tmp_path):
    root = tmp_path / "Beat Saber"
    (root / "Beat Saber_Data" / "CustomLevels").mkdir(parents=True)
    (root / "BeatSaberVersion.txt").write_text("1.40.8\n", encoding="utf-8")
    return root


def make(tmp_path, game_root=None, mods=None, running=False, env=None):
    settings = Settings(tmp_path / "s.db")
    if game_root is not None:
        settings.set_game_dir(str(game_root))
    mods = mods or FakeMods()
    pm = PlaylistManagerMod(
        settings,
        tmp_path / "levels",
        lambda: mods,
        env=env,
        running=lambda: running,
        background=False,
    )
    return pm, mods


def test_without_a_game_folder_the_status_explains_the_mount(tmp_path):
    pm, _ = make(tmp_path)
    got = pm.status()
    assert got["game"]["state"] == "not_mounted"
    assert got["mod"]["github"] == GITHUB == "https://github.com/rithik-b/PlaylistManager"
    assert "GAME_DIR_HOST" in got["mount_help"]["env"]
    assert any("/game" in line for line in got["mount_help"]["compose"])
    assert got["mod"]["can_install"] is False


def test_a_configured_game_reports_its_version_and_catalog(tmp_path, game):
    pm, mods = make(tmp_path, game)
    got = pm.status()
    assert got["game"] == {
        "state": "ready",
        "path": str(game.resolve()),
        "source": "setting",
        "version": "1.40.8",
        "running": False,
    }
    assert got["catalog"]["state"] == "ready"
    assert mods.versions.count("1.40.8") == 1
    assert got["mod"]["state"] == "missing"
    assert got["mod"]["available_version"] == "1.7.3"
    assert got["mod"]["can_install"] is False  # BSIPA is missing: it needs ModAssistant
    assert "BSIPA" in got["mod"]["reason"]
    assert [d["name"] for d in got["mod"]["dependencies"]] == [
        "BSIPA",
        "SongCore",
        "BeatSaberPlaylistsLib",
    ]


def with_bsipa(game):
    (game / "IPA" / "Data" / "Managed").mkdir(parents=True)
    (game / "IPA" / "Data" / "Managed" / "IPA.Injector.dll").write_bytes(b"ipa")


def test_install_adds_the_mod_and_missing_dependencies_only(tmp_path, game):
    with_bsipa(game)
    pm, mods = make(tmp_path, game)
    assert pm.status()["mod"]["can_install"] is True
    pm.install()
    assert (game / "Plugins" / "PlaylistManager.dll").read_bytes() == b"pm"
    assert (game / "Plugins" / "SongCore.dll").read_bytes() == b"sc"
    assert (game / "Libs" / "BeatSaberPlaylistsLib.dll").read_bytes() == b"lib"
    assert sorted(mods.downloads) == ["BeatSaberPlaylistsLib", "PlaylistManager", "SongCore"]
    done = pm.status()
    assert done["install"]["state"] == "done"
    assert done["mod"]["state"] == "current" and done["mod"]["installed_version"] == "1.7.3"
    assert done["mod"]["can_install"] is False


def test_an_installed_dependency_of_another_version_is_left_alone(tmp_path, game):
    with_bsipa(game)
    (game / "Plugins").mkdir()
    (game / "Plugins" / "SongCore.dll").write_bytes(b"a newer songcore")
    pm, mods = make(tmp_path, game)
    pm.install()
    assert (game / "Plugins" / "SongCore.dll").read_bytes() == b"a newer songcore"
    assert "SongCore" not in mods.downloads
    by_name = {d["name"]: d for d in pm.status()["mod"]["dependencies"]}
    assert by_name["SongCore"]["state"] == "other"


def test_install_is_refused_while_the_game_runs(tmp_path, game):
    with_bsipa(game)
    pm, mods = make(tmp_path, game, running=True)
    assert pm.status()["mod"]["can_install"] is False
    with pytest.raises(PermissionError, match="running"):
        pm.install()
    assert mods.downloads == []


def test_install_is_refused_without_a_game_folder(tmp_path):
    pm, _ = make(tmp_path)
    with pytest.raises(PermissionError, match="game folder"):
        pm.install()


def test_install_is_refused_when_bsipa_is_missing(tmp_path, game):
    pm, mods = make(tmp_path, game)
    with pytest.raises(PermissionError, match="BSIPA"):
        pm.install()
    assert mods.downloads == []


def test_a_game_version_without_builds_is_reported_as_unsupported(tmp_path, game):
    pm, _ = make(tmp_path, game, mods=FakeMods(supported=False))
    got = pm.status()
    assert got["mod"]["state"] == "unsupported"
    assert "1.40.8" in got["mod"]["reason"]


def test_a_catalogue_failure_is_reported_not_raised(tmp_path, game):
    pm, _ = make(tmp_path, game, mods=FakeMods(fail="could not reach BeatMods"))
    got = pm.status()
    assert got["catalog"] == {"state": "failed", "error": "could not reach BeatMods"}
    assert got["mod"]["can_install"] is False


def test_a_failed_download_leaves_the_game_folder_untouched(tmp_path, game):
    with_bsipa(game)

    class Bad(FakeMods):
        def download(self, build):
            if build.name == "PlaylistManager":
                raise BeatModsError("hash mismatch")
            return super().download(build)

    pm, _ = make(tmp_path, game, mods=Bad())
    pm.install()
    assert pm.status()["install"] == {"state": "failed", "message": "hash mismatch"}
    assert not (game / "Plugins" / "SongCore.dll").exists()
    assert not (game / "Libs").exists()


def test_the_game_folder_comes_from_the_env_when_no_setting(tmp_path, game):
    pm, _ = make(tmp_path, env=str(game))
    got = pm.status()
    assert got["game"]["state"] == "ready" and got["game"]["source"] == "env"


def test_a_second_install_while_one_runs_is_refused(tmp_path, game):
    with_bsipa(game)
    pm, _ = make(tmp_path, game)
    pm._install_state = {"state": "running", "message": "Downloading"}
    with pytest.raises(PermissionError, match="already"):
        pm.install()
