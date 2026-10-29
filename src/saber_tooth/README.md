# saber_tooth

The application package. Module design is in [architecture](../../docs/architecture.md).

Subpackages:

1. [mapio/](mapio/README.md): read and write Beat Saber maps.
2. [checks/](checks/README.md): one pure function per quality rule.
3. [fixer/](fixer/README.md): turns findings into verified edit proposals.
4. [generator/](generator/README.md): rule-based note placement.
5. [lightshow/](lightshow/README.md): learn and apply lightshow templates.
6. [service/](service/README.md): library refresh, scan, one-step generate, apply and learn.
7. [web/](web/README.md): build output of the browser UI from [frontend](../../frontend/README.md).
8. [crop/](crop/README.md): crop a map to a 1 or 2 minute highlight.
9. [vr/](vr/README.md): VR headset runtime detection, standard library only.

Top-level modules:

1. `model.py`: internal map model (notes, bombs, walls, events, difficulties).
2. `profiles.py`: per-difficulty generation profiles.
3. `analysis.py`, `analyser_client.py`, `audio.py`: beat-analyser output, its HTTP client, audio conversion, cutting and tag reading.
4. `timing.py`, `swings.py`: beat and time conversion, swing geometry.
5. `assemble.py`: builds a map from generator output.
6. `store.py`, `store_maps.py`, `store_claims.py`: SQLite storage, map queries and proposal claims.
7. `jobs.py`: one worker thread drains the `jobs` table oldest first through handlers registered per kind; queued jobs survive a restart.
8. `store_jobs.py`: job rows, the durable queue: create (with per-map dedupe), claim oldest first, progress, cancel, lists, restart cleanup, finished-row retention (one per map, global cap).
9. `safe_fs.py`: path safety helpers.
10. `cli.py`: the `saber-tooth` command line.
11. `autofix.py`: offline scan, approve-all, apply and re-check loop behind `saber-tooth autofix`.
12. `songmeta.py`: song name, sub name and author from a video title (the analyser's project name) or audio tags.

Test with `task st:test`.
