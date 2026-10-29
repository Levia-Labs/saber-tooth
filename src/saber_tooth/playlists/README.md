# playlists

Local playlists for Beat Saber. The `.bplist` file is the only interface to the game.

1. `songcore.py`: `songcore_hash(folder)`, SHA1 over Info.dat then each listed difficulty file, uppercase hex (v2/v3 and v4 layouts); `HashCache` keys by file names, mtimes and sizes so a rewrite always misses.
2. `store.py`: `PlaylistStore` (one JSON file and optional cover per playlist) and the input validation.
3. `resolve.py`: `Library` (rows by id, hash index), `resolve_song` (current hash, `missing` when nothing installed matches) and `to_doc` (the live `.bplist`).

Document writing and the subfolder rule live in [beatsaver/playlists.py](../beatsaver/playlists.py); routes in [api/playlists_routes.py](../api/playlists_routes.py) (see [api.md](../../../docs/api.md#playlists)).

Tests: `task st:test -- tests/test_songcore_hash.py tests/test_api_playlists.py`. Parent: [saber_tooth](../README.md).
