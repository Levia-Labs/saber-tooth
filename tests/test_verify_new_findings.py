from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.checks.finding import Finding
from saber_tooth.fixer.verify import _RANK, _same, new_findings

finding = st.builds(
    Finding,
    rule=st.sampled_from(["a", "b"]),
    difficulty=st.sampled_from(["Hard", "Expert"]),
    beat_start=st.integers(0, 20).map(float),
    beat_end=st.integers(0, 20).map(float),
    severity=st.sampled_from(["warn", "error"]),
    message=st.just("m"),
)


def _slow(after, before):
    out = []
    for a in after:
        rank = [_RANK[b.severity] for b in before if _same(a, b)]
        if not rank or _RANK[a.severity] > max(rank):
            out.append(a)
    return out


@given(st.lists(finding, max_size=12), st.lists(finding, max_size=12))
def test_new_findings_matches_the_pairwise_definition(after, before):
    assert new_findings(after, before) == _slow(after, before)


def test_new_findings_scales_to_thousands_of_findings():
    many = [Finding("a", "Hard", float(i), float(i), "warn", "m") for i in range(4000)]
    assert new_findings(many, many) == []
