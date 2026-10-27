from hypothesis import given
from hypothesis import strategies as st

from saber_tooth.beatsaver.playlist_query import parse_playlist_query

KEYS = ["q", "order", "min_nps", "maps_min", "maps_max", "min_rating", "cursor", "from", "curated"]


@given(st.dictionaries(st.sampled_from(KEYS), st.text(max_size=40)))
def test_parse_never_raises_other_than_value_error(params):
    try:
        query = parse_playlist_query(params)
    except ValueError:
        return
    assert query.server["order"] in ("Latest", "Relevance", "Rating", "Curated")
    assert "includeEmpty" not in query.server and query.cursor >= 0
