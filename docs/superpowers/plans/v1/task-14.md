### Task 14 (Lane C): beat-analyser client and audio encoding

**Files:**

- Create: `src/saber_tooth/analyser_client.py`, `src/saber_tooth/audio.py`
- Test: `tests/test_analyser_client.py`

**Interfaces:**

- Produces: `AnalyserClient(base_url: str, uploads: Path, transport: httpx.BaseTransport | None = None)` with `analyse_url(url: str) -> Analysis` and `analyse_file(path: Path, name: str) -> Analysis`; both POST without an `Origin` header, read the project name from the `Content-Disposition` filename `<name>_tracks.zip`, then `read_project(uploads / name)`. Errors raise `AnalyserError(message)` using the JSON `error` field. `encode_egg(wav: Path, egg: Path) -> None` runs `ffmpeg -y -loglevel error -i <wav> -c:a libvorbis -q:a 6 -f ogg <egg>` via `subprocess.run([...], check=True)` with a list argument (no shell).

- [ ] **Step 0:** Read `app/storage.py` in the beat-analyser checkout and `app.py:103-147` to confirm how the project name is derived from an upload filename and from a YouTube URL; record the rule in `docs/architecture.md`. If the name is not recoverable from `Content-Disposition`, fall back to `GET /folders` and pick the entry whose meta `name` matches, newest first.
- [ ] **Step 1: Write failing tests** with `httpx.MockTransport`: success path returns `Analysis` read from a temp uploads dir; error JSON becomes `AnalyserError("too long")`; request has no `Origin` header.
- [ ] **Steps 2-4:** fail, implement, pass. **Step 5:** Commit `feat: add beat-analyser client and ogg encoder`.
