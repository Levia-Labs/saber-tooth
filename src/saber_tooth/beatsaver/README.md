# beatsaver

Search, filter and download BeatSaver maps and playlists. Design: [spec](../../../docs/superpowers/specs/2026-10-27-beatsaver-integration-design.md).

1. `client.py`: rate-limited httpx client restricted to api.beatsaver.com and `*.beatsaver.com` downloads.
2. `models.py`: `BsMap`, `BsDiff`, `BsPlaylist` parsed from API JSON.
3. `cache.py`: `BsCache`, SQLite cache of map details (24 h) and query pages (10 min).
4. `filters.py`: `LocalFilter` (difficulties, NPS, rating) and `ServerQuery` (BeatSaver parameters).
5. `search.py`: cursor search over BeatSaver pages; the cursor `page.offset` always advances.
6. `download.py`, `naming.py`: safe zip extraction, install into CustomLevels, folder names.
7. `playlists.py`: `.bplist` export that never overwrites.
8. `params.py`, `presets.py`: validated query-string parsing and saved filter presets.

Tests: `task st:test -- tests/test_beatsaver_client.py tests/test_beatsaver_cache.py tests/test_beatsaver_search.py tests/test_beatsaver_download.py tests/test_beatsaver_playlists.py tests/test_api_beatsaver.py tests/test_api_beatsaver_more.py`, using [fixtures](../../../tests/fixtures/beatsaver/README.md). Parent: [saber_tooth](../README.md).
