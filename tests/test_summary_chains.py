"""Findings summary counts one map per chain, like maps_with_findings."""

import shutil
import time

from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.findings_summary import findings_summary, maps_with_findings
from saber_tooth.service import map_id_for
from tests.test_fix_map import NAME, _make
from tests.test_regenerate import _finding

COPY = f"{NAME} [saber-tooth]"


def _settle(svc):
    """Wait out the background copy-scan backfill so it cannot overwrite injected scans."""
    for _ in range(200):
        with svc._bg_lock:
            if not svc._backfilling and not svc._pending_scans:
                return
        time.sleep(0.05)


def _scan(svc, folder, *findings):
    scan = {"findings": list(findings), "analysis": None}
    svc.store.replace_open_proposals(map_id_for(folder), [], scan)


def _with_copy(tmp_path):
    svc = _make(tmp_path)
    shutil.copytree(svc.levels / NAME, svc.levels / COPY)
    svc.refresh_library()
    _settle(svc)
    return svc


def test_original_with_clean_copy_contributes_nothing(tmp_path):
    svc = _with_copy(tmp_path)
    _scan(svc, NAME, _finding("a"), _finding("b"))
    _scan(svc, COPY)
    out = findings_summary(svc.store, svc.levels)
    assert out["findings"] == 0 and out["rules"] == []
    assert out["maps"]["with_findings"] == 0 and out["maps_with_findings"] == []
    assert out["maps"]["total"] == 1


def test_original_without_copy_counts(tmp_path):
    svc = _make(tmp_path)
    _scan(svc, NAME, _finding("a"), _finding("a"))
    out = findings_summary(svc.store, svc.levels)
    assert out["findings"] == 2 and out["maps"]["with_findings"] == 1
    assert out["maps_with_findings"] == [
        {"id": map_id_for(NAME), "folder": NAME, "rules": {"a": 2}}
    ]


def test_copy_with_findings_counts_instead_of_original(tmp_path):
    svc = _with_copy(tmp_path)
    _scan(svc, NAME, _finding("a"))
    _scan(svc, COPY, _finding("b"))
    out = findings_summary(svc.store, svc.levels)
    assert [m["folder"] for m in out["maps_with_findings"]] == [COPY]
    assert {r["rule"] for r in out["rules"]} == {"b"}
    assert out["maps_with_findings"][0]["id"] in maps_with_findings(svc.store)


@settings(max_examples=15, deadline=None)
@given(
    orig=st.lists(st.sampled_from("abc"), max_size=4),
    copy=st.lists(st.sampled_from("abc"), max_size=4),
    has_copy=st.booleans(),
)
def test_totals_equal_sum_over_maps_with_findings(tmp_path_factory, orig, copy, has_copy):
    svc = _make(tmp_path_factory.mktemp("s"))
    if has_copy:
        shutil.copytree(svc.levels / NAME, svc.levels / COPY)
        svc.refresh_library()
        _settle(svc)
        _scan(svc, COPY, *[_finding(r) for r in copy])
    _scan(svc, NAME, *[_finding(r) for r in orig])
    out = findings_summary(svc.store, svc.levels)
    per = {}
    for m in out["maps_with_findings"]:
        for rule, n in m["rules"].items():
            per[rule] = per.get(rule, 0) + n
    by_rule = {}
    for r in out["rules"]:
        by_rule[r["rule"]] = by_rule.get(r["rule"], 0) + r["findings"]
    assert per == by_rule
    assert sum(per.values()) == out["findings"]
    assert {m["id"] for m in out["maps_with_findings"]} == set(maps_with_findings(svc.store))
