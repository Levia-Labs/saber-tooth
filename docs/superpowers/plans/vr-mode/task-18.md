# Task 18: Browser-check and smoke routes

`task st:browser-check` loads each route in a headless browser and fails on any console error or an empty page; it gains `/vr`, `/vr/beatsaver` and, when the library has a map, `/vr/maps/<id>`. It stays read-only (every non-GET request is aborted). `task st:smoke` checks that the server answers the three client routes with HTML and that `/api/vr/status` answers 200 with a `source` field; with no helper that is `source: "none"`, which is a pass. The browser run itself needs a running stack and a browser, so it is a manual gate for the receipt; the unit tests here pin the route lists.

**Files:**

- Modify: `scripts/browser_check.mjs` (the `routes` lines)
- Modify: `scripts/smoke.py` (route tuple, one check)
- Modify: `tests/test_script_smoke.py` (default routes, two tests)
- Test: `tests/test_script_browser_check.py`

**Interfaces:**

Consumes: `smoke.run_checks(base, fetch)` and the `make_fetch` helper in `tests/test_script_smoke.py`.

Produces: `browser_check.mjs` visits `/`, `/maps/<id>`, `/vr/maps/<id>` (when a map exists), `/beatsaver`, `/beatsaver/playlists`, `/about`, `/vr`, `/vr/beatsaver`; `smoke.run_checks` adds the checks `html /vr`, `html /vr/maps/x`, `html /vr/beatsaver` and `api vr status`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_script_browser_check.py`:

```python
"""scripts/browser_check.mjs: the route list and the failure rule, read as text; no browser runs."""

from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "browser_check.mjs"
TEXT = SCRIPT.read_text(encoding="utf-8")


def routes_block() -> str:
    start = TEXT.index("const routes = [")
    return TEXT[start : TEXT.index("const profile", start)]


def test_the_vr_routes_are_loaded():
    block = routes_block()
    assert '"/vr"' in block
    assert '"/vr/beatsaver"' in block
    assert "`/vr/maps/${mapId}`" in block


def test_the_desktop_routes_are_kept():
    block = routes_block()
    for route in ('"/"', '"/beatsaver"', '"/beatsaver/playlists"', '"/about"', "`/maps/${mapId}`"):
        assert route in block


def test_any_console_error_or_page_error_still_fails_the_check():
    assert 'm.type() === "error"' in TEXT
    assert "pageerror" in TEXT


def test_the_check_stays_read_only():
    assert '["GET", "HEAD"].includes(req.method())' in TEXT
```

In `tests/test_script_smoke.py`, add the new default routes to `make_fetch` (inside the `routes` dict, after `"/new"`):

```python
        "/vr": (200, "text/html", INDEX),
        "/vr/maps/x": (200, "text/html", INDEX),
        "/vr/beatsaver": (200, "text/html", INDEX),
        "/api/vr/status": (200, "application/json", b'{"source": "none", "runtime": null}'),
```

and append two tests at the end of the file:

```python
def test_vr_routes_and_status_are_checked():
    names = {n for n, _, _ in smoke.run_checks("http://h", make_fetch())}
    assert {"html /vr", "html /vr/maps/x", "html /vr/beatsaver", "api vr status"} <= names


def test_a_missing_vr_route_or_status_fails_its_own_check():
    fetch = make_fetch(
        {"/vr/beatsaver": (404, "", b""), "/api/vr/status": (200, "application/json", b"{}")}
    )
    failed = {n for n, ok, _ in smoke.run_checks("http://h", fetch) if not ok}
    assert failed == {"html /vr/beatsaver", "api vr status"}
```

- [ ] **Step 2: Run them to see them fail**

Run: `rtk proxy uv run pytest -q tests/test_script_browser_check.py tests/test_script_smoke.py`
Expected: FAIL: `test_the_vr_routes_are_loaded` (`'"/vr"'` not in the routes block) and `test_vr_routes_and_status_are_checked` (the names are missing).

- [ ] **Step 3: Implement**

In `scripts/browser_check.mjs`, replace

```js
const routes = ["/", "/beatsaver", "/beatsaver/playlists", "/about"];
if (mapId) routes.splice(1, 0, `/maps/${mapId}`);
```

with

```js
const routes = ["/", "/beatsaver", "/beatsaver/playlists", "/about", "/vr", "/vr/beatsaver"];
if (mapId) routes.splice(1, 0, `/maps/${mapId}`, `/vr/maps/${mapId}`);
```

In `scripts/smoke.py`, change the route tuple in `run_checks`:

```python
    for route in ("/", "/maps/x", "/new", "/vr", "/vr/maps/x", "/vr/beatsaver"):
```

and add, after the `api facets` check:

```python
    status, _, body = fetch(f"{base}/api/vr/status", None)
    add("api vr status", status == 200 and b'"source"' in body, str(status))
```

- [ ] **Step 4: Run them to see them pass**

Run: `rtk proxy uv run pytest -q tests/test_script_browser_check.py tests/test_script_smoke.py`
Expected: PASS (4 new tests in the first file, 2 new in the second).

- [ ] **Step 5: Run the browser check against a running stack (manual gate)**

Run: `task st:browser-check`
Expected: `chrome /vr`, `chrome /vr/beatsaver` and, with a map, `chrome /vr/maps/<id>` lines each with a character count, and no `console:` or `pageerror:` lines. If no stack or browser is available in the lane, the receipt says `browser-check: not run`.

- [ ] **Step 6: Commit**

Commit: main thread runs `task st:commit -- -m "test(vr): browser-check and smoke cover the VR routes and status" scripts/browser_check.mjs scripts/smoke.py tests/test_script_smoke.py tests/test_script_browser_check.py`
