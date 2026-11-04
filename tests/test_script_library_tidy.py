"""Tests for scripts/library_tidy.py with a fake request; no network."""

import json

from hypothesis import given
from hypothesis import strategies as st

from tests.script_loader import load

lt = load("library_tidy")
Item = lt.Item
F = "ab12 (Song - Me)"


def test_chain_key():
    assert lt.chain_key(F) == (F, 0, 0)
    assert lt.chain_key(F + " [saber-tooth]") == (F, 1, 1)
    assert lt.chain_key(F + " [saber-tooth 3]") == (F, 1, 3)
    assert lt.chain_key(F + " [saber-tooth] [saber-tooth 2]") == (F, 2, 2)
    assert lt.chain_key("st-abc [saber-tooth]") == ("st-abc [saber-tooth]", 0, 0)


def test_clean_title():
    t = "Song [crop 10-60] [Monstercat Release] [2 min] [saber-tooth 2]  [saber-tooth]"
    assert lt.clean_title(t) == "Song [Monstercat Release]"


def test_original_only_renamed():
    p = lt.plan([Item("1", F, "Song", 200)])
    assert p.chains == 1 and not p.delete and not p.rename
    assert p.keep == (Item("1", F, "Song", 200),)


def test_newest_generation_with_duration():
    items = [
        Item("o", F, "Song", 200),
        Item("a", F + " [saber-tooth]", "Song [saber-tooth]", 200),
        Item("b", F + " [saber-tooth] [saber-tooth]", "Song [saber-tooth]", 10),
        Item("c", F + " [saber-tooth] [saber-tooth 2]", "Song [crop 1-2]", 40),
    ]
    p = lt.plan(items)
    assert sorted(i.id for i in p.keep) == ["c", "o"]
    assert sorted(i.id for i in p.delete) == ["a", "b"]
    assert p.rename[0][1] == "Song [saber-tooth]"


def test_crop_then_highest_n():
    items = [
        Item("a", F + " [saber-tooth 2]", "Song", 60),
        Item("b", F + " [saber-tooth 3]", "Song", 60),
        Item("c", F + " [saber-tooth 1]", "Song [crop 0-60]", 60),
    ]
    assert [i.id for i in lt.plan(items).keep] == ["c"]
    assert [i.id for i in lt.plan(items[:2]).keep] == ["b"]


def test_generated_own_chain_and_no_rename_when_equal():
    items = [Item("1", "st-1", "A [saber-tooth]", 90), Item("2", "st-2", "B [saber-tooth]", 90)]
    p = lt.plan(items)
    assert p.chains == 2 and not p.delete and not p.rename


def test_generated_renamed_never_deleted():
    p = lt.plan([Item("1", "st-1", "A [crop 1-2]", 90)])
    assert not p.delete and p.rename[0][1] == "A [saber-tooth]"


def test_hidden_ids():
    out = lt.with_hidden([Item("1", "a")], ["a", "b"])
    assert out[1] == Item(lt.map_id_for("b"), "b")
    assert len(out[1].id) == 12


@given(
    st.lists(
        st.tuples(st.integers(1, 3), st.integers(1, 3), st.integers(0, 100)),
        min_size=1,
        max_size=8,
    )
)
def test_plan_keeps_one_per_chain(rows):
    items = [
        Item(str(i), F + " [saber-tooth]" * (g - 1) + f" [saber-tooth {n}]", "S", d)
        for i, (g, n, d) in enumerate(rows)
    ]
    items.append(Item("orig", F, "S", 100))
    p = lt.plan(items)
    assert p.chains == 1
    assert "orig" not in {i.id for i in p.delete}
    assert [i.id for i in p.keep if i.id != "orig"] and len(p.keep) == 2
    assert len(p.keep) + len(p.delete) == len(items)


def make_request(pages, fail=()):
    calls = []

    def request(method, url, body):
        calls.append((method, url, body))
        if method == "GET":
            offset = int(url.rsplit("=", 1)[1])
            return 200, json.dumps({"items": pages.get(offset, [])}).encode()
        if method == "POST" and url.endswith("/api/maps/delete"):
            ids = json.loads(body)["ids"]
            if any(i in fail for i in ids):
                return 500, b""
            results = [{"id": i, "status": "deleted", "reasons": []} for i in ids]
            return 200, json.dumps({"results": results}).encode()
        return (500 if url.rsplit("/", 1)[1] in fail else 200), b""

    return request, calls


def rows(n, start=0):
    return [{"id": f"i{start + k}", "folder": f"f{start + k}", "title": "T"} for k in range(n)]


def test_fetch_pages():
    request, _ = make_request({0: rows(100), 100: rows(5, 100)})
    assert len(lt.fetch_items("http://x", request)) == 105


def _valid_map(folder):
    folder.mkdir(parents=True)
    info = {
        "_version": "2.0.0",
        "_songName": "S",
        "_songFilename": "song.ogg",
        "_difficultyBeatmapSets": [
            {"_difficultyBeatmaps": [{"_difficulty": "Easy", "_beatmapFilename": "Easy.dat"}]}
        ],
    }
    (folder / "Info.dat").write_text(json.dumps(info), encoding="utf-8")
    (folder / "Easy.dat").write_text("{}", encoding="utf-8")
    (folder / "song.ogg").write_bytes(b"x")


def test_main_dry_and_apply(capsys, tmp_path):
    levels = tmp_path / "levels"
    c1, c2 = F + " [saber-tooth]", F + " [saber-tooth 2]"
    levels.mkdir()
    ids = {f: lt.map_id_for(f) for f in (F, c1, c2)}
    pages = {
        0: [
            {"id": ids[F], "folder": F, "title": "Song", "duration_s": 100},
            {
                "id": ids[c1],
                "folder": c1,
                "title": "Song [saber-tooth]",
                "duration_s": 99,
            },
        ]
    }
    base = ["--base", "http://x", "--levels", str(levels)]
    request, calls = make_request(pages)
    assert lt.main(["--base", "http://x"], request) == 0
    assert capsys.readouterr().out.startswith("chains=1 keep=2 delete=0 rename=0")
    assert all(c[0] == "GET" for c in calls)
    assert lt.main([*base, "--apply"], request) == 0
    assert [c[0] for c in calls[1:]] == ["GET"]
    _valid_map(levels / c2)
    pages[0].append({"id": ids[c2], "folder": c2, "title": "Song", "duration_s": 9})
    request, calls = make_request(pages)
    assert lt.main([*base, "--apply"], request) == 0
    assert [c[0] for c in calls[1:]] == ["POST"]
    assert calls[-1][1].endswith("/api/maps/delete")
    assert json.loads(calls[-1][2]) == {"ids": [ids[c2]]}
    pages[0][1]["title"] = "Song [crop 1-2]"
    request, calls = make_request(pages)
    assert lt.main([*base, "--apply"], request) == 0
    assert json.loads(calls[-1][2]) == {"name": "Song [saber-tooth]", "keep_folder": True}
    request, _ = make_request(pages, fail=(ids[c2],))
    assert lt.main([*base, "--apply"], request) == 1
    assert "failed=1 refused=0" in capsys.readouterr().out


def test_apply_requires_levels(capsys):
    request, calls = make_request({0: rows(2)})
    assert lt.main(["--base", "http://x", "--apply"], request) == 2
    assert "--levels" in capsys.readouterr().out
    assert calls == []


def test_apply_skips_refused_folders(capsys, tmp_path):
    levels = tmp_path / "levels"
    c1, c2 = F + " [saber-tooth]", F + " [saber-tooth 2]"
    _valid_map(levels / c2)
    (levels / c2 / "notes.txt").write_text("keep", encoding="utf-8")
    ids = {f: lt.map_id_for(f) for f in (F, c1, c2)}
    pages = {
        0: [
            {"id": ids[F], "folder": F, "title": "Song", "duration_s": 100},
            {"id": ids[c1], "folder": c1, "title": "Song", "duration_s": 99},
            {"id": ids[c2], "folder": c2, "title": "Song", "duration_s": 9},
        ]
    }
    request, calls = make_request(pages)
    argv = ["--base", "http://x", "--levels", str(levels), "--apply"]
    assert lt.main(argv, request) == 0
    out = capsys.readouterr().out
    assert "refused=1" in out and "notes.txt" in out
    assert all(c[0] not in ("DELETE", "POST") for c in calls)
    assert (levels / c2 / "notes.txt").exists()


def test_drop_originals_only_in_chains_with_copy():
    items = [
        Item("o", F, "Song", 200),
        Item("c", F + " [saber-tooth]", "Song [saber-tooth]", 200),
        Item("lone", "zz (Other - Me)", "Other", 200),
        Item("g", "st-1", "G [saber-tooth]", 90),
    ]
    p = lt.plan(items, originals="drop")
    assert sorted(i.id for i in p.keep) == ["c", "g", "lone"]
    assert [i.id for i in p.delete] == ["o"]
    assert p.drop_ids == frozenset({"c"})


def test_drop_rename_has_no_keep_folder():
    items = [Item("o", F, "Song", 200), Item("c", F + " [saber-tooth]", "Song [crop 1-2]", 200)]
    request, calls = make_request({})
    count, _, _ = lt.apply_plan("http://x", lt.plan(items, originals="drop"), request)
    assert count == 0
    assert json.loads(calls[-1][2]) == {"name": "Song [saber-tooth]"}
    calls.clear()
    lt.apply_plan("http://x", lt.plan(items), request)
    assert json.loads(calls[-1][2])["keep_folder"] is True


@given(
    st.lists(
        st.tuples(st.integers(1, 3), st.integers(1, 3), st.integers(0, 100)),
        min_size=1,
        max_size=8,
    )
)
def test_drop_keeps_one_copy_per_chain(rows):
    items = [
        Item(str(i), F + " [saber-tooth]" * (g - 1) + f" [saber-tooth {n}]", "S", d)
        for i, (g, n, d) in enumerate(rows)
    ]
    items.append(Item("orig", F, "S", 100))
    p = lt.plan(items, originals="drop")
    assert len(p.keep) == 1 and p.keep[0].id != "orig"
    assert len(p.keep) + len(p.delete) == len(items)


def _batch_request(statuses):
    calls = []

    def request(method, url, body):
        calls.append((method, url, body))
        ids = json.loads(body)["ids"]
        res = [{"id": i, "status": statuses.get(i, "deleted"), "reasons": ["r"]} for i in ids]
        return 200, json.dumps({"results": res}).encode()

    return request, calls


def test_deletes_go_in_batches_of_50_and_aggregate(tmp_path):
    levels = tmp_path / "levels"
    items = [Item(lt.map_id_for(f"m{k}"), f"m{k}") for k in range(120)]
    for it in items:
        _valid_map(levels / it.folder)
    plan = lt.Plan(1, (), tuple(items), (), frozenset())
    statuses = {items[3].id: "refused", items[60].id: "busy", items[99].id: "missing"}
    request, calls = _batch_request(statuses)
    failed, lines, refused = lt.apply_plan("http://x", plan, request, levels=levels)
    assert [len(json.loads(c[2])["ids"]) for c in calls] == [50, 50, 20]
    assert all(c[0] == "POST" for c in calls)
    assert (failed, refused) == (1, 1)
    assert any("busy" in line for line in lines)
