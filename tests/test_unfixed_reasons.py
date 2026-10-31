"""Fix stores why it left a finding unfixed on the copy's scan; the findings API returns it."""

import pytest
from fastapi.testclient import TestClient

from saber_tooth.api import create_app
from saber_tooth.checks import Finding
from saber_tooth.service import fix as fix_mod
from saber_tooth.service import map_id_for
from saber_tooth.service.fixsave import with_reasons
from tests.test_fix_map import CLASH
from tests.test_service import NAME, _make

STUCK = Finding("flip-cut", "Hard", 8.0, 9.0, "error", "hand flips")


def _unfixable(monkeypatch, reason="no verified fix"):
    real_fix, real_checks = fix_mod.fix_beatmap, fix_mod.run_checks

    def fix(*args, **kw):
        run = real_fix(*args, **kw)
        run.unfixed = [{**STUCK.to_dict(), "reason": reason}]
        return run

    monkeypatch.setattr(fix_mod, "fix_beatmap", fix)
    monkeypatch.setattr(fix_mod, "run_checks", lambda *a, **k: [*real_checks(*a, **k), STUCK])


def _findings(svc, mid):
    with TestClient(create_app(svc), base_url="http://localhost") as c:
        return c.get(f"/api/maps/{mid}/findings").json()["findings"]


def test_fix_stores_the_reason_on_the_copy_and_the_api_returns_it(tmp_path, monkeypatch):
    svc = _make(tmp_path, extra=CLASH)
    _unfixable(monkeypatch, "verify rejected: parity break")
    copy = svc.fix_map(map_id_for(NAME))["fixed_id"]
    [f] = _findings(svc, copy)
    assert f["unfixed_reason"] == "verify rejected: parity break"


def test_a_finding_with_no_reason_reports_null(tmp_path):
    svc = _make(tmp_path)
    svc.store.replace_open_proposals(
        map_id_for(NAME), [], {"findings": [STUCK.to_dict()], "analysis": None}
    )
    assert _findings(svc, map_id_for(NAME))[0]["unfixed_reason"] is None


def test_a_later_scan_clears_stale_reasons(tmp_path, monkeypatch):
    svc = _make(tmp_path, extra=CLASH)
    _unfixable(monkeypatch)
    copy = svc.fix_map(map_id_for(NAME))["fixed_id"]
    svc.store.replace_open_proposals(copy, [], {"findings": [STUCK.to_dict()], "analysis": None})
    assert _findings(svc, copy)[0]["unfixed_reason"] is None


def test_reasons_match_on_rule_difficulty_and_window():
    other = {**STUCK.to_dict(), "beat_start": 20.0, "beat_end": 21.0}
    out = with_reasons([STUCK.to_dict(), other], [{**STUCK.to_dict(), "reason": "budget"}])
    assert [f.get("unfixed_reason") for f in out] == ["budget", None]


@pytest.mark.parametrize("unfixed", [[], [{"rule": "x"}]])
def test_malformed_or_empty_reasons_leave_findings_alone(unfixed):
    assert with_reasons([STUCK.to_dict()], unfixed) == [STUCK.to_dict()]
