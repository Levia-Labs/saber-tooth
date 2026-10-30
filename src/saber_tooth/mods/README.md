# mods

Beat Saber mod management for the game folder the service can reach.

1. `game.py`: finds the install (saved setting, `GAME_DIR`, or two folders above a `Beat Saber_Data/CustomLevels` mount), reads `BeatSaberVersion.txt` and detects a running game where processes are visible.
2. `beatmods.py`: the BeatMods client (`/api/mods`, `/cdn/mod/<md5>.zip`), response parsing and dependency resolution. No proxy variables, no redirects, size caps, MD5 check on every download.
3. `extract.py`: zip entry path rules (only the plugin, library and loader-patch folders), hash checks and exclusive-create writes that never overwrite an existing file.
4. `playlistmanager.py`: status (installed, available, dependencies, blockers) and the install worker behind `/api/mods/playlistmanager`.

Tests: `tests/test_mods_*.py` use fakes for the network and a temporary game folder.
