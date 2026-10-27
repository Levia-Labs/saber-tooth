# beatsaver

Search, filter and download BeatSaver maps and playlists. Design: [spec](../../../docs/superpowers/specs/2026-10-27-beatsaver-integration-design.md).

1. `client.py`: rate-limited httpx client restricted to api.beatsaver.com and `*.beatsaver.com` downloads.
2. `models.py`: `BsMap`, `BsDiff`, `BsPlaylist` parsed from API JSON.

Tests: `task st:test -- tests/test_beatsaver_client.py`, using [fixtures](../../../tests/fixtures/beatsaver/README.md). Parent: [saber_tooth](../README.md).
