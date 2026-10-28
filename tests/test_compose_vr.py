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
    assert "0.0.0.0" not in COMPOSE.read_text(encoding="utf-8")  # noqa: S104


def test_the_helper_url_and_allowed_hosts_are_passed_through():
    text = block("saber-tooth")
    assert "VR_AGENT_URL: ${VR_AGENT_URL:-}" in text
    assert "SABER_ALLOWED_HOSTS: ${SABER_ALLOWED_HOSTS:-}" in text
