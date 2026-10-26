### Task 15: Service layer (scan, generate, apply)

**Files:**

- Create: `src/saber_tooth/service.py`
- Test: `tests/test_service.py`

**Interfaces:**

- Consumes: Tasks 3, 5, 6, 9, 10, 12, 13, 14.
- Produces: `Service(levels: Path, data: Path, store: Store, client: AnalyserClient, encode)` with `refresh_library() -> int`, `scan(map_id) -> int` (analyses the map's audio through `client.analyse_file` for `empty-gap` and `missing-difficulty`; stores proposals; returns count), `generate(url_or_path) -> int` (stages into `data/staging/<job>`, creates one `create-map` proposal), `apply(map_id) -> Path`, `learn() -> int`. Map id: first 12 hex chars of `sha1(folder_name)`.

Apply algorithm:

1. Load original, apply all approved ops in proposal id order.
2. Run checks; if any `error` remains, or any finding exists that was not in the original scan, abort with `ApplyConflict` naming the proposal ids whose op beats overlap the new findings; nothing is written.
3. Set `_songName` suffix, write via `LevelsWriter.new_folder` then `commit(unique_name(original + " [saber-tooth]"))`, copying audio, cover and any other non-`.dat` files from the original.
4. Mark applied proposals `applied`.

- [ ] **Step 1: Write failing tests** (temp `levels` with a copy of fixture `v2_basic`, mocked client):

```python
def test_apply_twice_creates_numbered_folder(svc, levels):
    ...
    # approve one proposal, apply, rescan, approve, apply again
    # assert folders "<name> [saber-tooth]" and "<name> [saber-tooth 2]" exist and original bytes unchanged


def test_conflicting_proposals_abort(svc, levels):
    ...
    # craft two approved Move ops that put a note into the same cell as another note
    # assert ApplyConflict lists both ids and no new folder exists


def test_original_untouched(svc, levels):
    ...
    # hash every file in the original before and after scan+apply
```

Write each with full bodies in the test file; use a `svc` fixture building `Service` over `tmp_path`.

- [ ] **Steps 2-4:** fail, implement, pass. **Step 5:** Commit `feat: add scan, generate and apply service`.
