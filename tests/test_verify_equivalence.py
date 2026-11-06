"""Verdict helpers keep the answers of their previous pairwise definitions."""

from hypothesis import given, settings
from hypothesis import strategies as st

from saber_tooth.checks.finding import Finding
from saber_tooth.fixer import verify
from saber_tooth.model import Color, Cut, Note

finding_st = st.builds(
    lambda rule, hands, s, ln, sev: Finding(
        rule,
        "Expert",
        s * 0.5,
        s * 0.5 + ln * 0.5,
        sev,
        "m",
        tuple(Note(s * 0.5, 0, 0, Color(h), Cut.ANY) for h in hands),
    ),
    st.sampled_from(["a", "b"]),
    st.lists(st.integers(0, 1), min_size=1, max_size=2),
    st.integers(0, 12),
    st.integers(0, 4),
    st.sampled_from(["warn", "error"]),
)


def _key(f):
    return (f.difficulty, f.rule, frozenset(int(n.color) for n in f.notes), f.walls)


def _old_target_remains(target, before, after):
    others: dict = {}
    for b in before:
        if b is not target:
            others.setdefault(_key(b), []).append(b)
    return any(
        verify._overlaps(a, target)
        and not any(verify._overlaps(a, o) for o in others.get(_key(a), ()))
        for a in after
    )


def _old_new_findings(after, before):
    return [
        a
        for a in after
        if not any(
            _key(b) == _key(a)
            and b.beat_end >= a.beat_start - verify.EPS
            and b.beat_start <= a.beat_end + verify.EPS
            and verify._RANK[b.severity] >= verify._RANK[a.severity]
            for b in before
        )
    ]


def _old_same(a, b):
    ranges = a.beat_start <= b.beat_end + verify.EPS and b.beat_start <= a.beat_end + verify.EPS
    return _key(a) == _key(b) and ranges


@settings(max_examples=300, deadline=None)
@given(st.lists(finding_st, min_size=1, max_size=25), st.lists(finding_st, max_size=25), st.data())
def test_verdict_helpers_match_the_pairwise_definitions(before, after, data):
    target = data.draw(st.sampled_from(before))
    assert verify._target_remains(target, before, after) == _old_target_remains(
        target, before, after
    )
    assert verify.new_findings(after, before) == _old_new_findings(after, before)
    for a in after:
        assert verify._same(a, target) == _old_same(a, target)
