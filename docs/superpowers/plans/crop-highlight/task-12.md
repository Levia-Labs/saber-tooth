# Task 12: MCP tools

**Files:**

- Modify: `src/saber_tooth/api/mcp_tools.py`
- Modify: `src/saber_tooth/api/__init__.py`
- Modify: `tests/test_mcp.py`

**Interfaces:**

Consumes: `CropApi.timeline(raw)`, `CropApi.crop(raw, start, end)` (Task 11); `READ`, `JOB` annotations in `mcp_tools.py`.

Produces: `build_mcp(api: Api, bs: BeatSaverApi | None = None, crop: CropApi | None = None) -> MCPServer` with two more tools when `crop` is given:

```python
map_timeline(map_id: str) -> dict          # READ: same JSON as GET /api/maps/{id}/timeline
crop_map(map_id: str, start_beat: float, end_beat: float) -> dict   # JOB: same as POST /api/maps/{id}/crop, returns {"job"}
```

- [ ] **Step 1: Write the failing test**

In `tests/test_mcp.py`, change the `TOOLS` set to include `"map_timeline"` and `"crop_map"` (add them to the last line of the set literal: `"beatsaver_search", "beatsaver_download", "map_timeline", "crop_map",`) and change `READ_ONLY` to:

```python
READ_ONLY = {"list_maps", "get_proposals", "job_status", "beatsaver_search", "map_timeline"}
```

Append to `tests/test_mcp.py`:

```python
def test_map_timeline_tool_returns_the_contract(client):
    data = call(client, "map_timeline", map_id=MID)["structuredContent"]
    assert data["map_id"] == MID and set(data["lengths"]) == {"60", "120"}
    assert data["lengths"]["60"]["enabled"] is False  # the fixture song is 3 s long


def test_crop_map_tool_reports_a_broken_window_as_an_error(client):
    result = call(client, "crop_map", map_id=MID, start_beat=5.0, end_beat=9.0)
    assert result["isError"] is True
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest tests/test_mcp.py -q`
Expected: FAIL: `test_initialize_and_list_tools` shows the tool set lacks `map_timeline` and `crop_map`.

- [ ] **Step 3: Implement**

In `src/saber_tooth/api/mcp_tools.py` add `from saber_tooth.api.crop_api import CropApi` after the `from saber_tooth.api.core import Api` import, change the signature to:

```python
def build_mcp(
    api: Api, bs: BeatSaverApi | None = None, crop: CropApi | None = None
) -> MCPServer:
```

and replace the block

```python
if bs is not None:
    _beatsaver_tools(mcp, bs)
return mcp
```

with:

```python
if bs is not None:
    _beatsaver_tools(mcp, bs)
if crop is not None:
    _crop_tools(mcp, crop)
return mcp
```

Append at the end of the file:

```python
def _crop_tools(mcp: MCPServer, crop: CropApi) -> None:
    @mcp.tool(annotations=READ)
    def map_timeline(map_id: str) -> dict[str, Any]:
        """Notes per second per difficulty, the song sections with intensity and, for 1 and
        2 minute crops, the suggested windows and every allowed start and end point. Times are
        in beats and seconds; an analysed map gives better sections than `map_only` ones."""
        return crop.timeline(map_id)

    @mcp.tool(annotations=JOB)
    def crop_map(map_id: str, start_beat: float, end_beat: float) -> dict[str, Any]:
        """Crop a map to a 1 or 2 minute highlight: writes a new '<map> [1 min]' or
        '[2 min]' folder; the original is never changed. start_beat and end_beat must be a start
        and an allowed end from map_timeline. Returns a job id for job_status."""
        return crop.crop(map_id, start_beat, end_beat)
```

In `src/saber_tooth/api/__init__.py` change `build_mcp(api, bs).streamable_http_app(` to `build_mcp(api, bs, crop_api).streamable_http_app(`.

- [ ] **Step 4: Run to pass**

Run: `uv run pytest tests/test_mcp.py tests/test_api_crop.py -q`
Expected: all pass.

- [ ] **Step 5: Lint**

Run: `uv run ruff check src/saber_tooth/api/mcp_tools.py src/saber_tooth/api/__init__.py tests/test_mcp.py && uv run ruff format --check src/saber_tooth/api/mcp_tools.py tests/test_mcp.py`
Expected: no findings. Do not run `ruff format` on `api/__init__.py`: it carries another lane's uncommitted edits.

- [ ] **Step 6: Commit:** main thread runs `task git:commit -- "feat: map_timeline and crop_map MCP tools"` (subagents never commit).
