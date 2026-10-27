# BeatSaver Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Search, filter and download BeatSaver maps and playlists from saber-tooth, with local filters BeatSaver
lacks (required difficulty sets, per-difficulty NPS), saved presets, and downloads into CustomLevels.

**Architecture:** New backend package `src/saber_tooth/beatsaver/` (client, models, cache, filters, search, download,
playlists) behind new `/api/beatsaver/*` routes and two MCP tools; new React view at `/beatsaver` with a header
switch. Server-side filters go to BeatSaver; difficulty and NPS filters run locally over cached map details.

**Tech Stack:** Python 3.12, httpx, SQLite (stdlib), FastAPI, hypothesis; React 19 + TS, TanStack Query/Virtual,
Radix UI, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-27-beatsaver-integration-design.md`

## Global Constraints

1. Network: only `https://api.beatsaver.com` for API calls; downloads only from https hosts ending in `.beatsaver.com`
   taken from `versions[].downloadURL`; `User-Agent: saber-tooth/<version> (+https://github.com/Levia-Labs/saber-tooth)`;
   at most 5 requests per second; backoff on 429/5xx honouring `Retry-After` (cap 60 s, 4 retries).
2. Tests never call the network: `httpx.MockTransport` with JSON fixtures under `tests/fixtures/beatsaver/`.
3. Downloads: zip <= 100 MB, uncompressed <= 400 MB, <= 500 entries, no absolute paths, `..`, drive letters or
   symlinks; validated with `mapio.load_map`; committed only through `LevelsWriter` as
   `<key> (<songName> - <levelAuthorName>)` with `<>:"/\|?*` and control characters removed; never overwrite.
4. Seeded preset "Gentle full-spread hits": diffs Easy,Normal,Hard mode all; min rating 0.95; NPS 1-2 scope any;
   tags `electronic|dubstep|rock|metal|punk|j-rock|techno|house|trance|drum-and-bass`; order Rating descending.
5. Repo rules: files <= 300 lines, lines <= 100, `encoding="utf-8"`, no em dashes in docs, parametrised SQL with
   whitelisted sort/filter keys, lanes in git worktrees (`task st:lane`), commits via `task st:commit`, gate via
   `task st:gate`.

## Review Focus

1. A map with Easy/Normal/Hard only in a non-Standard characteristic (e.g. OneSaber) must not match the difficulty
   filter (Task 3 test `test_requires_standard_characteristic`).
2. A BeatSaver page where every map fails local filters must not stall infinite scroll: the cursor advances and the
   response reports `scanned` > 0 with zero items (Task 3 test `test_cursor_advances_past_empty_pages`).
3. A zip whose map folder is nested one level deep (`Song/Info.dat`) must install (common in older uploads), while a
   zip with two Info.dat files is refused (Task 4 test `test_nested_single_root_installs`).
4. Downloading a map already in the library (same BeatSaver key or same hash) is skipped, not duplicated (Task 4 test
   `test_installed_map_is_skipped`).
5. BeatSaver returning 429 mid-scan keeps the partial result and returns a retry hint instead of a 500 (Task 6 test
   `test_rate_limited_search_returns_partial`).

---

### Task 1: BeatSaver client and models

**Files:**

- Create: `src/saber_tooth/beatsaver/__init__.py`, `client.py`, `models.py`, `README.md`
- Create: `tests/fixtures/beatsaver/search_page0.json`, `map_detail.json`, `playlist_page0.json`, `README.md`
- Test: `tests/test_beatsaver_client.py`

**Interfaces:**

- Produces: `BeatSaverClient(transport: httpx.BaseTransport | None = None, rate: float = 5.0)` with
  `search(params: dict[str, str], page: int) -> list[BsMap]`, `maps_by_ids(ids: list[str]) -> list[BsMap]`,
  `playlist_search(params, page) -> list[BsPlaylist]`, `playlist_page(pid: int, page: int) -> list[BsMap]`,
  `download(url: str, dest: Path, max_bytes: int) -> Path`; `BeatSaverError(message, retry_after: float | None)`.
- `BsMap(id, name, song_name, song_sub, song_author, mapper, bpm, duration, score, upvotes, downvotes, tags,
ranked, hash, download_url, cover_url, preview_url, diffs: tuple[BsDiff, ...], uploaded)`;
  `BsDiff(characteristic, difficulty, nps, njs, notes, seconds)`; `BsPlaylist(id, name, owner, maps_count, min_nps,
max_nps, cover_url)`; `BsMap.from_json(d) -> BsMap` tolerant of missing keys; uses the latest published version.

- [ ] Step 1: tests: parse fixtures; host allowlist rejects `http://` and non-beatsaver hosts for download; 429 with
      Retry-After 2 retries then succeeds (fake clock injected); rate limiter spaces calls >= 0.2 s (fake clock);
      download aborts over max_bytes. Step 2: run, fail. Step 3: implement. Step 4: pass. Step 5: commit
      `feat: BeatSaver API client and models`.

### Task 2: Cache tables

**Files:** Create `src/saber_tooth/beatsaver/cache.py`; Modify `src/saber_tooth/store.py` (schema migration hook
only if store owns migrations); Test `tests/test_beatsaver_cache.py`.

**Interfaces:** `BsCache(db_path: Path)` with `put_maps(maps: list[BsMap])`, `get_maps(ids) -> dict[str, BsMap]`
(entries older than 24 h ignored), `put_query(key: str, page: int, ids: list[str])`,
`get_query(key, page) -> list[str] | None` (10 min TTL), `clock` injectable. Tables `bs_maps(id TEXT PRIMARY KEY,
hash TEXT, json TEXT, fetched_at REAL)`, `bs_queries(key TEXT, page INTEGER, ids TEXT, fetched_at REAL,
PRIMARY KEY(key, page))`.

- [ ] Steps: tests for TTL expiry, round trip of BsMap JSON, migration on an existing database; implement; commit
      `feat: cache BeatSaver maps and query pages`.

### Task 3: Local filters and cursor search

**Files:** Create `src/saber_tooth/beatsaver/filters.py`, `search.py`; Test `tests/test_beatsaver_search.py`.

**Interfaces:**

- `LocalFilter(diffs: frozenset[str] = frozenset(), diffs_mode: Literal["all","any"] = "all",
nps_min: float | None = None, nps_max: float | None = None, nps_scope: Literal["any","all"] = "any",
characteristic: str = "Standard", min_rating: float | None = None)` with `matches(m: BsMap) -> bool`.
- `ServerQuery(q="", tags: tuple[str, ...] = (), min_rating=None, order="Rating", ascending=False, ranked=False,
date_from=None, date_to=None, bpm_min=None, bpm_max=None, duration_min=None, duration_max=None,
full_spread=False)` with `to_params() -> dict[str, str]` (tags joined with `|`; minNps/maxNps widened: send
  `maxNps` only when nps_scope is "all"; never send minNps for scope any).
- `search(client, cache, server: ServerQuery, local: LocalFilter, cursor: str | None, limit: int = 40,
max_pages: int = 10) -> SearchResult(items: list[BsMap], cursor: str | None, scanned: int, matched: int,
partial_reason: str | None)`; cursor encodes `(page, offset)` as `"p.o"`.
- Required tests (exact):

```python
def test_requires_standard_characteristic(make_map):
    m = make_map(
        diffs=[("OneSaber", "Easy", 1.5), ("OneSaber", "Normal", 1.5), ("OneSaber", "Hard", 1.5)]
    )
    f = LocalFilter(diffs=frozenset({"Easy", "Normal", "Hard"}))
    assert not f.matches(m)


def test_nps_scope_any(make_map):
    m = make_map(
        diffs=[("Standard", "Easy", 0.8), ("Standard", "Normal", 1.4), ("Standard", "Hard", 2.6)]
    )
    assert LocalFilter(nps_min=1, nps_max=2, nps_scope="any").matches(m)
    assert not LocalFilter(nps_min=1, nps_max=2, nps_scope="all").matches(m)


def test_cursor_advances_past_empty_pages(fake_client_with_pages):
    # pages 0..2 contain no matching maps, page 3 has one
    res = search(
        fake_client_with_pages,
        cache,
        ServerQuery(),
        LocalFilter(diffs=frozenset({"Easy"})),
        cursor=None,
        limit=5,
        max_pages=2,
    )
    assert res.items == [] and res.scanned > 0 and res.cursor == "2.0"
```

- Hypothesis property: paging a fixed fake result set with random limits yields every matching id exactly once.
- [ ] Commit `feat: local BeatSaver filters and cursor search`.

### Task 4: Safe download and install

**Files:** Create `src/saber_tooth/beatsaver/download.py`, `naming.py`; Modify `src/saber_tooth/store.py` /
`store_maps.py` (add nullable `bs_id`, `bs_hash` to maps, migrate in place); Test `tests/test_beatsaver_download.py`
with zips built in-test.

**Interfaces:** `install(client, writer: LevelsWriter, store, bs: BsMap, tmp: Path) -> InstallOutcome(status:
Literal["installed","skipped","failed"], reason: str | None, folder: str | None)`; `safe_extract(zip_path: Path,
dest: Path, max_total: int, max_entries: int) -> Path` (returns the folder that holds Info.dat, unwrapping a single
nested root); `folder_name_for(bs: BsMap) -> str`.

- [ ] Tests: traversal (`../x`), absolute (`/x`, `C:/x`), symlink entry, too many entries, too large, corrupt zip,
      two Info.dat refused, nested single root installs, Noodle map refused with reason, installed map skipped by bs_id
      and by hash, success writes the folder, records bs_id/bs_hash, original folders untouched. Commit
      `feat: safe BeatSaver downloads into CustomLevels`.

### Task 5: Playlists and .bplist export

**Files:** Create `src/saber_tooth/beatsaver/playlists.py`; Test `tests/test_beatsaver_playlists.py`.

**Interfaces:** `export_bplist(title: str, maps: list[BsMap], dest_dir: Path, cover: bytes | None = None) -> Path`
(file name sanitised, never overwrite: append ` (2)`), JSON `{"playlistTitle", "playlistAuthor": "saber-tooth",
"songs": [{"key", "hash", "songName", "levelAuthorName"}], "image": "base64,..." optional}`.

- [ ] Tests: JSON shape, sanitised name, no overwrite, refusal when dest_dir is unset. Commit
      `feat: BeatSaver playlist export`.

### Task 6: API routes, presets, MCP

**Files:** Create `src/saber_tooth/api/beatsaver.py`, `src/saber_tooth/beatsaver/presets.py`; Modify
`src/saber_tooth/api/__init__.py`, `api/mcp_tools.py`, `docker-compose.yml` (optional `PLAYLISTS_DIR` bind from env
`PLAYLISTS_DIR_HOST`), `.env.example`, `docs/api.md`; Test `tests/test_api_beatsaver.py`.

**Interfaces:** routes exactly as the spec's API section; query parsing into `ServerQuery`/`LocalFilter` with bounds
(limit 1-100, ratings 0-1, nps 0-30); `POST /api/beatsaver/download {ids}` max 100 ids -> `{"job": id}` using the
existing Jobs worker; presets CRUD with the seeded preset from Global Constraints 4; `GET /api/beatsaver/config`
-> `{"playlists_enabled": bool}`.

- [ ] Tests: every route, 400 on bad params, 413/400 on >100 ids, job result per map,
      `test_rate_limited_search_returns_partial`, presets seeded once, MCP tools listed and callable with fakes. Commit
      `feat: BeatSaver API routes, presets and MCP tools`.

### Task 7: Frontend BeatSaver view

**Files:** Create `frontend/src/pages/BeatSaverPage.tsx`, `frontend/src/components/beatsaver/*` (table, row,
filters, presets bar, selection bar), `frontend/src/api/beatsaver.ts`, `frontend/src/lib/bsfilters.ts`; Modify
router, header (Library | BeatSaver segmented switch), styles; Test `frontend/tests/beatsaver*.test.tsx`.

**Interfaces:** consumes the Task 6 routes; URL state mirrors every filter; table columns Image, Title, Author,
Levels (outline chips Ea/No/Ha/Ex/Ex+ with NPS in Tip), Rating, Length/BPM, Tags, Status (Installed/downloading/
failed), Actions (Download, Preview, Open on BeatSaver in a new tab with rel="noopener noreferrer"); selection with
"Download N" (confirmation listing new vs already installed) and "Export playlist" (only when playlists_enabled);
footer "Scanned N BeatSaver maps, M match"; presets chips with the seeded preset first and "Save current filters".

- [ ] Tests: URL round trip, preset apply/save, selection counts, confirmation, download job progress rendering,
      partial/rate-limit banner with retry. Commit `feat: BeatSaver view with filters, presets and downloads`.

### Task 8: Frontend playlists tab

**Files:** Create `frontend/src/pages/BeatSaverPlaylistsPage.tsx`, `frontend/src/components/beatsaver/PlaylistList.tsx`;
Modify router (`/beatsaver/playlists`, `/beatsaver/playlists/:id`); Test `frontend/tests/beatsaverPlaylists.test.tsx`.

- [ ] Tests: search, open playlist, local filters applied, "Download all matching". Commit
      `feat: BeatSaver playlists tab`.

### Task 9: Docs and final gate

**Files:** `docs/architecture.md`, `README.md`, `docs/adr/0013-beatsaver-proxy-and-local-filters.md`, folder
READMEs. Run `task st:gate`, rebuild with `task st:up`, `task st:smoke`. Commit `docs: BeatSaver integration`.

## Execution lanes

1. Lane `bs-backend`: Tasks 1-6 in order (one implementer, task reviews between).
2. Lane `bs-frontend`: Tasks 7-8, starting immediately against the spec's API contract; merges after Task 6 lands.
3. Task 9 on main after both lanes merge.
