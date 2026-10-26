### Task 18: Docker, compose, final docs

**Files:**

- Create: `Dockerfile`, `docker-compose.yml`, `.dockerignore`
- Modify: `README.md`, `docs/architecture.md`, `docs/api.md`, `TODO.md`

`Dockerfile`: `python:3.12-slim`, `apt-get install -y --no-install-recommends ffmpeg`, copy `uv` from `ghcr.io/astral-sh/uv:0.11`, `uv sync --frozen --no-dev`, non-root user `app`, `EXPOSE 8100`, `CMD ["uv","run","--no-sync","uvicorn","saber_tooth.api:app","--host","0.0.0.0","--port","8100"]`.

`docker-compose.yml`:

```yaml
services:
  saber-tooth:
    build: .
    image: saber-tooth:latest
    ports: ["127.0.0.1:${SABER_PORT:-8100}:8100"]
    environment:
      LEVELS_DIR: /levels
      DATA_DIR: /data
      ANALYSER_URL: http://beat-analyser:8000
      ANALYSER_UPLOADS: /analyser
    volumes:
      - "${LEVELS_DIR:?set LEVELS_DIR in .env}:/levels"
      - analyser-uploads:/analyser:ro
      - saber-data:/data
    depends_on: [beat-analyser]
  beat-analyser:
    image: levialabs/beat-analyser:latest
    environment:
      MAX_UPLOAD_MB: ${MAX_UPLOAD_MB:-200}
      YT_MAX_MINUTES: ${YT_MAX_MINUTES:-20}
    volumes: ["analyser-uploads:/app/uploads"]
    read_only: true
    tmpfs: ["/tmp"]
volumes:
  analyser-uploads:
  saber-data:
```

- [ ] **Step 1:** Add task `st:compose-check` running `docker compose config -q`. Run it. Expected: exit 0.
- [ ] **Step 2:** `task st:up`, then `curl -s http://127.0.0.1:8100/api/maps` returns JSON. Run `POST /api/lightshow/learn` and confirm a non-zero unit count in the job result.
- [ ] **Step 3:** Sync docs via `crepidoma:docs-syncer`; record v1 limitations in `TODO.md` via `task todo:add` (v4 audio-data BPM, non-Standard characteristics, bombs and walls in generator).
- [ ] **Step 4:** Full gate `task ci` (or the Crepidoma gate it exposes). Commit `feat: containerise saber-tooth with beat-analyser`.
