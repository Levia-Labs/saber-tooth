### Task 1: Crepidoma adoption and repo scaffold

**Agent:** `crepidoma:pillar-migrator` for steps 1-3, then main thread for steps 4-8.

**Files:**

- Create: `.gitmodules`, `.crepidoma/` (submodule), `Taskfile.yml`, `tasks/Taskfile.yml`, `.claude/settings.json`, `.claude/README.md`, `.pre-commit-config.yaml`, `CLAUDE.md`, `pyproject.toml`, `src/saber_tooth/__init__.py`, `tests/__init__.py`, `tests/test_smoke.py`, `.env.example`, `.gitattributes`
- Modify: `.gitignore`, `README.md`

- [ ] **Step 1:** Create branch `feat/v1` from `main`.
- [ ] **Step 2:** Follow the Crepidoma `docs/migration.md` steps 1-10 with the beat-analyser checkout as the reference: submodule at `.crepidoma`, Taskfile includes from `templates/Taskfile.includes.yml` (claude, lint, repo, todo, git, graph, test, quality, security, ci, rtk, setup; no `go`), settings from `templates/settings.json` (plugin `crepidoma@levia-labs`, `"model": "claude-opus-5-5"`, env `CLAUDE_CODE_SUBAGENT_MODEL=sonnet`), `.pre-commit-config.yaml`, `CLAUDE.md` from template.
- [ ] **Step 3:** Add `tasks/Taskfile.yml` included as namespace `st` with `vars: { PY: "{{.PY}}" }`:

```yaml
version: "3"
tasks:
  test:
    desc: Run the pytest suite. Usage: task st:test [-- <pytest args>]
    cmds: ["uv run pytest -q {{.CLI_ARGS}}"]
  check:
    desc: Run quality checks on one map folder. Usage: task st:check -- <folder>
    cmds: ["uv run saber-tooth check {{.CLI_ARGS}}"]
  inspect:
    desc: Summarise one map folder. Usage: task st:inspect -- <folder>
    cmds: ["uv run saber-tooth inspect {{.CLI_ARGS}}"]
  survey:
    desc: Read-only finding counts across a levels dir. Usage: task st:survey -- <levels_dir>
    cmds: ["uv run saber-tooth survey {{.CLI_ARGS}}"]
  learn:
    desc: Build lightshow templates. Usage: task st:learn -- <levels_dir> <out.json>
    cmds: ["uv run saber-tooth learn {{.CLI_ARGS}}"]
  up:
    desc: Build and start the compose stack. Usage: task st:up
    cmds: ["docker compose up -d --build"]
  down:
    desc: Stop the compose stack. Usage: task st:down
    cmds: ["docker compose down"]
  logs:
    desc: Tail saber-tooth logs. Usage: task st:logs
    cmds: ["docker compose logs --tail 100 saber-tooth"]
  gen:
    desc: Start a map generation job from a URL. Usage: task st:gen -- <url>
    cmds: ["uv run saber-tooth gen-url {{.CLI_ARGS}}"]
```

- [ ] **Step 4:** `pyproject.toml`:

```toml
[project]
name = "saber-tooth"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["fastapi>=0.115", "uvicorn[standard]>=0.32", "httpx>=0.27", "pillow>=11", "python-multipart>=0.0.12"]

[project.scripts]
saber-tooth = "saber_tooth.cli:main"

[dependency-groups]
dev = ["pytest>=8", "hypothesis>=6.100", "ruff>=0.7"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/saber_tooth"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 110
target-version = "py312"
```

- [ ] **Step 5:** `tests/test_smoke.py`: `def test_import(): import saber_tooth`. Run `uv sync` then `uv run pytest -q`. Expected: 1 passed.
- [ ] **Step 6:** `.env.example` with `LEVELS_DIR=X:/SteamLibrary/steamapps/common/Beat Saber/Beat Saber_Data/CustomLevels`, `SABER_PORT=8100`, `YT_MAX_MINUTES=20`, `MAX_UPLOAD_MB=200`. `.gitattributes`: `* text=auto eol=lf`. `.gitignore`: `.env`, `.venv/`, `data/`, `__pycache__/`.
- [ ] **Step 7:** Docs (normal prose, humanizer pass): `README.md` (purpose, quick start `task st:up`, tasks index), `TODO.md`, `docs/architecture.md`, `docs/map-format.md` (v2/v3/v4 key tables from Task 3), `docs/api.md` (routes from spec), `docs/adr/0001-vanilla-only-visuals.md` through `0006-single-process-fastapi-sqlite.md` (Context, Decision, Consequences each), `.claude/README.md` listing agents, skills and plugins, `.claude/agents/map-auditor.md` (haiku; runs `task st:check -- <folder>`, returns at most 10 lines of counts per rule), `.claude/agents/lightshow-learner.md` (sonnet; runs `task st:learn`, reports per-environment unit counts).
- [ ] **Step 8:** Commit: `task git:commit -- "chore: adopt Crepidoma and scaffold saber-tooth"`.
