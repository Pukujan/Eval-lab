"""Shared test configuration.

The suite must run with **no credentials and no services**. Two things enforce
that here: provider keys are stripped from the environment for the whole session,
and state is redirected to a per-session temporary directory so tests never write
into a developer's `var/`.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


@pytest.fixture(scope="session", autouse=True)
def _credential_free_environment() -> None:
    """Remove every provider credential before any test runs.

    If a test only passes because a real key happened to be exported, the suite is
    not credential-free and CI will disagree with the developer's machine.
    """
    for key in list(os.environ):
        if key.endswith(("_API_KEY", "_TOKEN", "_SECRET")) and key != "LITELLM_MASTER_KEY":
            os.environ.pop(key, None)
    os.environ.setdefault("LITELLM_MASTER_KEY", "sk-local-mock-only")
    os.environ.setdefault("ENABLE_LIVE_PROVIDERS", "false")
    # No collector: spans are still created, nothing is exported.
    os.environ.pop("PHOENIX_ENDPOINT", None)


@pytest.fixture(scope="session", autouse=True)
def _isolated_var_directory(_credential_free_environment) -> None:
    with tempfile.TemporaryDirectory(prefix="rws-test-var-") as directory:
        os.environ["VAR_DIR"] = directory
        yield


@pytest.fixture(autouse=True)
def _reset_fixture_sync_coordinator():
    """Leave the fixture's interleaving seam clean between tests."""
    yield
    fixture_root = REPOSITORY_ROOT / "fixtures" / "duplicate-job-processing"
    if str(fixture_root) in sys.path:
        try:
            from src import sync  # type: ignore[import-not-found]

            sync.set_coordinator(None)
        except Exception:  # noqa: BLE001, S110 - cleanup only; the fixture may not be importable
            pass
