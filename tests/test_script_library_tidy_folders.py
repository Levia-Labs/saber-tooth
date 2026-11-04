"""Legacy-tag chains and folder normalisation in scripts/library_tidy.py; fake request."""

import json

from tests.script_loader import load

lt = load("library_tidy")
Item = lt.Item
F = "ab12 (Song - Me)"


def test_legacy_tags_are_copy_suffixes():
    assert lt.chain_key(F + " [saber-tooth] [2 min]") == (F, 1, 1)
    assert lt.chain_key(F + " [crop 10-60]") == (F, 1, 1)
    assert lt.chain_key(F + " [2 min] [saber-tooth 2]") == (F, 1, 2)


def test_legacy_folder_chain_collapses_and_gets_folder_fix():
    legacy = F + " [saber-tooth] [2 min]"
    p = lt.plan([Item("o", F, "Song", 200), Item("c", legacy, "Song [saber-tooth] [2 min]", 120)])
    assert p.chains == 1 and [i.id for i in p.keep] == ["o", "c"]
    assert p.rename == (
        (Item("c", legacy, "Song [saber-tooth] [2 min]", 120), "Song [saber-tooth]"),
    )


def test_doubled_folder_with_clean_title_still_normalised():
    dbl = F + " [saber-tooth] [saber-tooth]"
    p = lt.plan([Item("c", dbl, "Song [saber-tooth]", 120)])
    assert [(i.id, n) for i, n in p.rename] == [("c", "Song [saber-tooth]")]
    ok = lt.plan([Item("c", F + " [saber-tooth]", "Song [saber-tooth]", 120)])
    assert not ok.rename


def test_conflict_reported_not_fatal():
    dbl = F + " [saber-tooth] [saber-tooth]"
    p = lt.plan([Item("c", dbl, "Song [saber-tooth]", 120)])
    seen = []

    def req(method, url, body):
        seen.append((method, json.loads(body)))
        return 409, b""

    count, lines, refused = lt.apply_plan("http://x", p, req)
    assert count == 0 and refused == 0 and lines[0].startswith("conflict c ")
    assert seen == [("PATCH", {"name": "Song [saber-tooth]", "keep_folder": True})]


def test_drop_mode_folder_only_fix_keeps_folder_flag():
    dbl = F + " [saber-tooth] [saber-tooth]"
    p = lt.plan([Item("o", F, "Song", 200), Item("c", dbl, "Song [saber-tooth]", 120)], "drop")
    seen = []

    def req(method, url, body):
        seen.append(json.loads(body)) if method == "PATCH" else None
        return 200, json.dumps({"results": []}).encode()

    lt.apply_plan("http://x", p, req)
    assert seen == [{"name": "Song [saber-tooth]", "keep_folder": True}]
