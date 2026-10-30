from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.store import Store
from saber_tooth.store_maps import CROP_MIN_LENGTH_S, LEVEL_NAMES, STATUS_VALUES, level_mask

FULL = level_mask(LEVEL_NAMES)


def _store(tmp_path, name="db.sqlite"):
    return Store(tmp_path / name)


def _add(store, mid, duration, scan, folder=None):
    store.upsert_map(mid, folder or mid, mid, "m", "E", None, 120.0, duration, FULL)
    if scan is not None:
        findings = [{"severity": scan, "rule": "r"}] if scan != "none" else []
        store.replace_open_proposals(mid, [], scan={"findings": findings, "analysis": None})


def _expected(duration, scan):
    if scan is None:
        return "unscanned"
    if scan == "error":
        return "error"
    if scan == "warning":
        return "warn"
    return "crop" if duration is not None and duration > CROP_MIN_LENGTH_S else "ok"


def test_crop_threshold_is_two_and_a_half_minutes():
    assert CROP_MIN_LENGTH_S == 150.0


@settings(max_examples=40, deadline=None)
@given(
    st.one_of(st.none(), st.floats(0, 600, allow_nan=False), st.sampled_from([150.0, 150.01])),
    st.sampled_from([None, "none", "error", "warning"]),
)
def test_status_rule_over_length_and_scan(duration, scan):
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:  # Windows keeps the db open
        store = _store(Path(d))
        _add(store, "a", duration, scan)
        assert store.query_maps()[0][0]["status"] == _expected(duration, scan)


def test_filter_facets_and_replacement_of_ok(tmp_path):
    store = _store(tmp_path)
    _add(store, "long", 200.0, "none")
    _add(store, "edge", 150.0, "none")
    _add(store, "short", 100.0, "none")
    _add(store, "unknown", None, "none")
    _add(store, "warned", 300.0, "warning")
    rows, total = store.query_maps(status=("crop",))
    assert [r["id"] for r in rows] == ["long"] and total == 1
    assert [r["id"] for r in store.query_maps(status=("ok",))[0]] == ["edge", "short", "unknown"]
    facet = store.facets()["status"]
    assert facet["crop"] == 1 and facet["ok"] == 3 and facet["warn"] == 1
    assert set(facet) == set(STATUS_VALUES) and "crop" in STATUS_VALUES


def test_crop_outputs_never_qualify_and_fixed_copies_follow_the_rule(tmp_path):
    store = _store(tmp_path)
    _add(store, "a", 400.0, "none", "Song [1 min]")
    _add(store, "b", 400.0, "none", "Song [2 min]")
    _add(store, "c", 400.0, "none", "Song [crop 2m30s]")
    _add(store, "d", 400.0, "none", "Song [saber-tooth]")
    status = {r["id"]: r["status"] for r in store.query_maps()[0]}
    assert status == {"a": "ok", "b": "ok", "c": "ok", "d": "crop"}
