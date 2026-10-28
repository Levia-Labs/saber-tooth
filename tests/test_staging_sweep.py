import os
import time

from saber_tooth.service.staging import STALE_AFTER_S, sweep_staging


def _folder(root, name, age_s):
    path = root / "staging" / name
    path.mkdir(parents=True)
    (path / "audio.egg").write_bytes(b"x")
    stamp = time.time() - age_s
    os.utime(path, (stamp, stamp))
    return path


def test_sweep_removes_old_staging_folders_and_keeps_recent_ones(tmp_path):
    old = _folder(tmp_path, "a" * 32, STALE_AFTER_S + 60)
    fresh = _folder(tmp_path, "b" * 32, 60)
    assert sweep_staging(tmp_path) == 1
    assert not old.exists() and fresh.exists()


def test_sweep_touches_nothing_outside_the_staging_dir(tmp_path):
    other = tmp_path / "levels" / "Song"
    other.mkdir(parents=True)
    stamp = time.time() - 10 * STALE_AFTER_S
    os.utime(other, (stamp, stamp))
    (tmp_path / "staging").mkdir()
    (tmp_path / "staging" / "note.txt").write_text("kept", encoding="utf-8")
    assert sweep_staging(tmp_path) == 0
    assert other.exists() and (tmp_path / "staging" / "note.txt").exists()


def test_sweep_without_a_staging_dir_does_nothing(tmp_path):
    assert sweep_staging(tmp_path) == 0
    assert not (tmp_path / "staging").exists()


def test_sweep_does_not_follow_a_symlinked_folder(tmp_path):
    target = tmp_path / "elsewhere"
    target.mkdir()
    (target / "keep.txt").write_text("kept", encoding="utf-8")
    (tmp_path / "staging").mkdir()
    link = tmp_path / "staging" / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        return  # symlinks unavailable on this machine
    assert sweep_staging(tmp_path, now=time.time() + 10 * STALE_AFTER_S) == 0
    assert (target / "keep.txt").exists()
