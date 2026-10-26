### Task 16: HTTP API and CLI gen-url

**Files:**

- Create: `src/saber_tooth/api.py`
- Modify: `src/saber_tooth/cli.py` (wire `gen-url`)
- Test: `tests/test_api.py`

**Interfaces:**

- Routes (spec): `GET /api/maps`, `POST /api/maps/{id}/scan` (returns `{"job": id}`), `GET /api/maps/{id}/proposals`, `POST /api/proposals/{id}/approve`, `POST /api/proposals/{id}/reject`, `POST /api/maps/{id}/approve-all`, `POST /api/maps/{id}/apply` (returns `{"job": id}`), `POST /api/generate` (JSON `{"url"}` or multipart `file`), `POST /api/lightshow/learn`, `GET /api/jobs/{id}`. Static frontend mounted at `/`. `create_app(service: Service) -> FastAPI`; module-level `app` built from env `LEVELS_DIR=/levels`, `DATA_DIR=/data`, `ANALYSER_URL=http://beat-analyser:8000`, `ANALYSER_UPLOADS=/analyser`.
- Errors: unknown map or proposal gives 404 JSON `{"error"}`; `ApplyConflict` gives job `failed` with message.

- [ ] **Step 1: Write failing tests** with `TestClient(create_app(fake_service))`: list maps, approve then reject transition, 404 on unknown id, generate with URL returns a job id.
- [ ] **Steps 2-4:** fail, implement, pass. **Step 5:** Commit `feat: expose HTTP API`.
