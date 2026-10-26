### Task 13 (Lane C): Store and job worker

**Files:**

- Create: `src/saber_tooth/store.py`, `src/saber_tooth/jobs.py`
- Test: `tests/test_store.py`, `tests/test_jobs.py`

**Interfaces:**

- Produces: `Store(path: Path)` with `upsert_map(id, folder, title, mapper, environment, parse_error)`, `list_maps() -> list[dict]`, `add_proposals(map_id, proposals: list[dict]) -> list[int]`, `proposals(map_id) -> list[dict]`, `set_status(proposal_id, status)`, `approved(map_id) -> list[dict]`, `create_job(kind) -> str`, `update_job(id, status, error=None, result=None)`, `job(id) -> dict`. Tables: `maps(id TEXT PK, folder, title, mapper, environment, parse_error, scanned_at)`, `jobs(id TEXT PK, kind, status, error, result_json, created_at, updated_at)`, `proposals(id INTEGER PK AUTOINCREMENT, map_id, rule, difficulty, severity, summary, ops_json, before_json, after_json, status, created_at)`. Status values: `pending, approved, rejected, applied`; job status `queued, running, done, failed`. `Jobs(store, max_workers=1)` with `submit(kind, fn, *args) -> job_id`; exceptions become `failed` with `str(exc)`.

- [ ] **Step 1: Write failing tests**: proposal status transitions; `set_status` on unknown id raises `KeyError`; a job whose function raises ends `failed` with the message; a job's result JSON round-trips.
- [ ] **Steps 2-4:** fail, implement (`sqlite3`, `check_same_thread=False`, one lock), pass. **Step 5:** Commit `feat: add sqlite store and job worker`.
