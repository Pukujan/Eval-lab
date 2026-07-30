"""Every declared service must have a health check and correct dependencies.

Parses `docker-compose.yml` statically, so it runs with no Docker daemon and no
network — the composition is checked even where the images cannot be pulled.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

COMPOSE_FILE = Path("docker-compose.yml")
EXPECTED_SERVICES = {"temporal", "phoenix", "litellm", "worker"}

#: Explicitly prohibited by the brief unless proven necessary.
PROHIBITED_IMAGES = ("redis", "postgres", "prometheus", "grafana", "kubernetes")


@pytest.fixture(scope="module")
def compose() -> dict:
    return yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))


def test_all_required_services_are_declared(compose: dict) -> None:
    assert set(compose["services"]) == EXPECTED_SERVICES


def test_every_service_declares_a_healthcheck(compose: dict) -> None:
    for name, service in compose["services"].items():
        assert "healthcheck" in service, f"service '{name}' has no health check"
        healthcheck = service["healthcheck"]
        assert healthcheck.get("test"), f"service '{name}' has an empty health check"
        assert "interval" in healthcheck and "retries" in healthcheck


def test_worker_waits_for_every_dependency_to_be_healthy(compose: dict) -> None:
    depends = compose["services"]["worker"]["depends_on"]
    assert set(depends) == {"temporal", "phoenix", "litellm"}
    for name, condition in depends.items():
        assert condition["condition"] == "service_healthy", (
            f"worker must wait for '{name}' to be healthy, not merely started"
        )


def test_every_image_is_digest_pinned(compose: dict) -> None:
    """A tag can be re-pointed; a digest cannot."""
    for name, service in compose["services"].items():
        image = service.get("image")
        if image is None:
            assert "build" in service, f"service '{name}' has neither image nor build"
            continue
        assert "@sha256:" in image, f"service '{name}' image is not digest-pinned: {image}"
        assert re.search(r"@sha256:[0-9a-f]{64}$", image), f"malformed digest on '{name}'"
        assert not image.endswith(":latest")


def test_no_prohibited_services(compose: dict) -> None:
    for name, service in compose["services"].items():
        image = (service.get("image") or "").lower()
        for prohibited in PROHIBITED_IMAGES:
            assert prohibited not in image, f"service '{name}' uses prohibited image {prohibited}"
            assert prohibited not in name.lower()


def test_temporal_uses_the_dev_server_with_sqlite(compose: dict) -> None:
    """No PostgreSQL: `start-dev` persists to a SQLite file (ADR-0005)."""
    command = " ".join(compose["services"]["temporal"]["command"])
    assert "start-dev" in command
    assert "--db-filename" in command
    assert "--ui-port=8233" in command


def test_phoenix_persists_to_sqlite(compose: dict) -> None:
    environment = compose["services"]["phoenix"]["environment"]
    assert environment["PHOENIX_SQL_DATABASE_URL"].startswith("sqlite:")
    assert compose["services"]["phoenix"]["volumes"], "Phoenix storage must be persistent"
    assert environment["PHOENIX_ENABLE_PROMETHEUS"] == "false"


def test_litellm_healthcheck_uses_the_unauthenticated_endpoint(compose: dict) -> None:
    """/health requires a virtual key in litellm 1.94.0; /health/readiness does not."""
    test = " ".join(compose["services"]["litellm"]["healthcheck"]["test"])
    assert "/health/readiness" in test


def test_no_secrets_are_committed_in_compose() -> None:
    raw = COMPOSE_FILE.read_text(encoding="utf-8")
    assert "sk-" not in raw.replace("sk-local-mock-only", "")
    for marker in ("OPENAI_API_KEY:", "ANTHROPIC_API_KEY:"):
        assert marker not in raw


def test_health_script_covers_every_service() -> None:
    source = Path("scripts/health.py").read_text(encoding="utf-8")
    for name in ("temporal", "phoenix", "litellm"):
        assert name in source, f"scripts/health.py does not check '{name}'"
