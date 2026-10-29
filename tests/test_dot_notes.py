"""Dot notes (Cut.ANY) have no swing direction: every direction lookup must cope with them."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.generator.placer import Placer, _link, _parity_clash
from saber_tooth.jobs import Jobs, error_text
from saber_tooth.model import CUT_VECTORS, OPPOSITE, Color, Cut, Note
from saber_tooth.profiles import PROFILES
from saber_tooth.store import Store
from saber_tooth.timing import Timing

TIMING = Timing(120.0, [])


def test_placer_places_after_a_dot_note_in_the_context():
    dot = Note(4.0, 1, 0, Color.RED, Cut.ANY)
    placer = Placer(TIMING, PROFILES["Expert"], [dot])
    assert placer.try_add(Color.RED, 5.0, [(Cut.UP, 1, 0)]) is not None  # was KeyError


def test_placer_places_before_a_dot_note_in_the_context():
    dot = Note(8.0, 1, 0, Color.RED, Cut.ANY)
    placer = Placer(TIMING, PROFILES["Expert"], [dot])
    assert placer.try_add(Color.RED, 6.0, [(Cut.DOWN, 1, 0)]) is not None


@given(st.sampled_from(list(Cut)), st.sampled_from(list(Cut)))
def test_every_cut_has_a_link_and_a_parity_answer(a, b):
    la = _link(Note(0.0, 1, 0, Color.RED, a), 0.0)
    lb = _link(Note(1.0, 1, 0, Color.RED, b), 1.0)
    assert isinstance(_parity_clash(la.vec, lb.vec), bool)
    if Cut.ANY in (a, b):
        assert _parity_clash(la.vec, lb.vec) is False


@given(st.sampled_from(list(Cut)))
def test_opposite_covers_every_cut_and_vectors_every_directional_cut(cut):
    assert OPPOSITE[OPPOSITE[cut]] == cut
    assert (cut in CUT_VECTORS) == (cut != Cut.ANY)


def test_a_key_error_reads_as_an_internal_error_not_a_bare_repr():
    assert error_text(KeyError(Cut.ANY)) == "internal error: missing entry for Cut.ANY"
    assert error_text(KeyError("x")) == "internal error: missing entry for 'x'"
    assert error_text(ValueError("bad")) == "bad"
    assert error_text(RuntimeError()) == "RuntimeError"


def test_a_job_that_raises_a_key_error_fails_with_the_readable_text(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    jobs = Jobs(store)

    def boom(args, progress):
        raise KeyError(Cut.ANY)

    jobs.register("boom", boom)
    job_id = store.create_job("boom", None, {})
    jobs.start()
    row = jobs.wait(job_id)
    jobs.shutdown()
    assert row["status"] == "failed"
    assert row["error"] == "internal error: missing entry for Cut.ANY"


@pytest.mark.parametrize("cut", [c for c in Cut if c != Cut.ANY])
def test_a_dot_never_clashes_with_any_direction(cut):
    assert not _parity_clash(None, CUT_VECTORS[cut])
    assert not _parity_clash(CUT_VECTORS[cut], None)
