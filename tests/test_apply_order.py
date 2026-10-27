"""Overlapping approved proposals apply in id order; stale ones are superseded or re-proposed."""

import pytest

from saber_tooth.fixer import Move
from saber_tooth.mapio import load_map
from saber_tooth.model import Color, Cut, Note
from saber_tooth.service import ApplyConflict, map_id_for
from tests.test_service import NAME, _make, _propose

BEAT = 166.3175048828125
BLUE = Note(BEAT, 0, 0, Color.BLUE, Cut.DOWN)
RED_A = Note(BEAT, 1, 1, Color.RED, Cut.DOWN)
RED_B = Note(BEAT, 2, 1, Color.RED, Cut.DOWN)


def _approved(svc, mid, rule):
    p = next(p for p in svc.store.proposals(mid) if p["rule"] == rule and p["difficulty"] == "Hard")
    svc.store.set_status(p["id"], "approved")
    return p["id"]


def _status(svc, mid):
    return {p["id"]: p["status"] for p in svc.store.proposals(mid)}


def test_user_case_crossover_then_stack_conflict(tmp_path):
    """Proposals 31 (crossover recolour) and 32 (move of the recoloured note), both approved."""
    svc = _make(tmp_path, extra=[BLUE, RED_A, RED_B])
    mid = map_id_for(NAME)
    svc.scan(mid)
    crossover = _approved(svc, mid, "crossover")
    stack = _approved(svc, mid, "stack-conflict")
    assert crossover < stack
    result = svc.run_apply(mid)  # used to fail: "move: note at beat 166.318 not found"
    assert result["applied"] == [crossover]
    assert result["superseded"] == [stack] and result["needs_review"] == []
    status = _status(svc, mid)
    assert (status[crossover], status[stack]) == ("applied", "superseded")
    written = load_map(svc.levels / result["folder"]).difficulties["Hard"].notes
    assert Note(BEAT, 2, 1, Color.BLUE, Cut.DOWN) in written
    assert Note(BEAT, 0, 0, Color.RED, Cut.DOWN) in written
    assert Note(BEAT, 2, 1, Color.RED, Cut.DOWN) not in written


def test_stale_proposal_with_a_live_finding_is_reproposed(tmp_path):
    svc = _make(tmp_path, extra=[RED_A, RED_B])
    mid = map_id_for(NAME)
    svc.scan(mid)
    scanned = next(p for p in svc.store.proposals(mid) if p["rule"] == "stack-conflict")
    svc.store.set_status(scanned["id"], "rejected")
    # an earlier approved edit moves the note the stack proposal targets; the stack stays
    earlier = _propose(svc, mid, [Move("Hard", RED_B, 3, 1, Cut.DOWN)])
    later = svc.store.add_proposals(mid, [scanned])[0]
    svc.store.set_status(later, "approved")
    # the stack is still an error after the earlier edit, so verification stops the write; the
    # stale proposal is superseded and its fresh replacement waits for review
    with pytest.raises(ApplyConflict, match="stack-conflict"):
        svc.apply(mid)
    status = _status(svc, mid)
    assert status[earlier] == "approved" and status[later] == "superseded"
    fresh = next(p for p in svc.store.proposals(mid) if p["replaces"] == later)
    assert fresh["status"] == "pending" and fresh["rule"] == "stack-conflict"
    assert fresh["finding"]["rule"] == "stack-conflict"
    svc.store.set_status(fresh["id"], "approved")
    result = svc.run_apply(mid)
    assert result["applied"] == [earlier, fresh["id"]] and result["superseded"] == []


def test_conflict_without_a_known_finding_still_aborts(tmp_path):
    svc = _make(tmp_path, extra=[BLUE, RED_B])
    mid = map_id_for(NAME)
    _propose(svc, mid, [Move("Hard", RED_B, 3, 2, Cut.DOWN)])
    _propose(svc, mid, [Move("Hard", RED_B, 1, 2, Cut.DOWN)])
    with pytest.raises(ApplyConflict, match="not found"):
        svc.apply(mid)
