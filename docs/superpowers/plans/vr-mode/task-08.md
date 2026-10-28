# Task 8: Compose: `extra_hosts`, `SABER_BIND` and `VR_AGENT_URL`

The container reaches the host helper as `host.docker.internal`; Docker Desktop defines that name, Linux hosts need the `host-gateway` entry. `SABER_BIND` (default `127.0.0.1`) sets the host address of the published port, so LAN access for a standalone headset is opt in; `SABER_ALLOWED_HOSTS` must then list the host names used. `VR_AGENT_URL` is passed through empty by default, which the client reads as "use the default URL" (Task 6). This is a container file change: after the unit test passes, `task st:compose-check` validates the file and the container e2e gate (`task st:release` dry run, then `task st:smoke` against a rebuilt stack) must run; if it is not run, the receipt says so.

**Files:**

- Modify: `docker-compose.yml`
- Modify: `.env.example` (append three commented lines)
- Test: `tests/test_compose_vr.py`

**Interfaces:**

Consumes: `docker-compose.yml` service `saber-tooth`.

Produces: the `saber-tooth` service has `ports: ["${SABER_BIND:-127.0.0.1}:${SABER_PORT:-8100}:8100"]`, `extra_hosts: ["host.docker.internal:host-gateway"]` and the environment entry `VR_AGENT_URL: ${VR_AGENT_URL:-}`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_compose_vr.py`:

```python
"""docker-compose.yml: the host alias for the VR helper and the opt-in LAN bind."""

import re
from pathlib import Path

COMPOSE = Path(__file__).resolve().parents[1] / "docker-compose.yml"


def block(name: str) -> str:
    """The lines of one top-level service (two-space indent) up to the next sibling."""
    lines = COMPOSE.read_text(encoding="utf-8").splitlines()
    start = lines.index(f"  {name}:")
    end = next(
        (i for i in range(start + 1, len(lines)) if re.match(r"^\S|^  \S", lines[i])), len(lines)
    )
    return "\n".join(lines[start:end])


def test_saber_tooth_reaches_the_host_through_host_gateway():
    assert 'extra_hosts: ["host.docker.internal:host-gateway"]' in block("saber-tooth")


def test_the_analyser_gets_no_host_alias():
    assert "extra_hosts" not in block("beat-analyser")


def test_the_published_port_binds_to_loopback_unless_saber_bind_says_otherwise():
    text = block("saber-tooth")
    assert 'ports: ["${SABER_BIND:-127.0.0.1}:${SABER_PORT:-8100}:8100"]' in text


def test_nothing_in_the_file_binds_all_interfaces_by_default():
    assert "0.0.0.0" not in COMPOSE.read_text(encoding="utf-8")


def test_the_helper_url_and_allowed_hosts_are_passed_through():
    text = block("saber-tooth")
    assert "VR_AGENT_URL: ${VR_AGENT_URL:-}" in text
    assert "SABER_ALLOWED_HOSTS: ${SABER_ALLOWED_HOSTS:-}" in text
```

- [ ] **Step 2: Run it to see it fail**

Run: `rtk proxy uv run pytest -q tests/test_compose_vr.py`
Expected: FAIL: `AssertionError` on `extra_hosts` (the first test).

- [ ] **Step 3: Implement**

In `docker-compose.yml`, replace the `ports` line of the `saber-tooth` service and add `extra_hosts` after it:

```yaml
ports: ["${SABER_BIND:-127.0.0.1}:${SABER_PORT:-8100}:8100"]
extra_hosts: ["host.docker.internal:host-gateway"]
```

Add one line to the same service's `environment` block, after `SABER_TRUSTED_PROXY_IPS`:

```yaml
VR_AGENT_URL: ${VR_AGENT_URL:-}
```

Append to `.env.example`:

```bash
# VR mode: where the container finds the host helper (`task st:vr-agent`). Default shown.
# VR_AGENT_URL=http://host.docker.internal:8101/status
# LAN access for a standalone headset browser. There is no login: anyone on the network can fix, crop, download and delete maps. Also list the host names in SABER_ALLOWED_HOSTS.
# SABER_BIND=0.0.0.0
```

- [ ] **Step 4: Run it to see it pass**

Run: `rtk proxy uv run pytest -q tests/test_compose_vr.py`
Expected: PASS, 5 passed.

- [ ] **Step 5: Validate the compose file**

Run: `rtk proxy task st:compose-check`
Expected: exit 0, no output. If Docker is not available in the lane, say `compose-check: not run` in the receipt.

- [ ] **Step 6: Commit**

Commit: main thread runs `task st:commit -- -m "feat(vr): compose host alias, SABER_BIND and VR_AGENT_URL" docker-compose.yml .env.example tests/test_compose_vr.py`
