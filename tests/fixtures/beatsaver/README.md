# tests/fixtures/beatsaver

Hand-built JSON shaped after the fields the BeatSaver API returns, served through `httpx.MockTransport`. No test calls the network.

1. `search_page0.json`: one search page, a full map with two versions and a sparse one.
2. `map_detail.json`: `/maps/ids` response keyed by id.
3. `playlist_page0.json`, `playlist_search.json`: playlist page and playlist search responses.

Used by [tests](../../README.md).
