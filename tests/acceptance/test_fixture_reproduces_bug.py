"""The known-bad fixture must reproduce the bug — deterministically."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.activities.patching import create_working_copy
from app.activities.probes import (
    concurrent_delivery_probe,
    delivery_contract_probe,
    sequential_redelivery_probe,
)
from app.config import FIXTURE_ROOT

pytestmark = pytest.mark.acceptance


@pytest.fixture
def working_copy(tmp_path: Path):
    copy = create_working_copy(destination_root=tmp_path)
    yield copy
    copy.cleanup()


def test_concurrent_delivery_duplicates_processing(working_copy) -> None:
    result = concurrent_delivery_probe(working_copy.path)
    assert result.exit_code == 0
    observations = result.observations

    assert observations["raw_result_rows"] == 2, "two rows should be committed for one job id"
    assert observations["effect_count"] == 2, "the external effect should fire twice"
    assert observations["invariant_holds"] is False
    assert observations["duplicate_processing"] is True


def test_reproduction_is_deterministic(working_copy) -> None:
    """Five runs, five identical results.

    A probe that reproduces a race "usually" is a coin flip that occasionally
    lies; the barrier in `src/sync.py` is what makes this exact every time.
    """
    observed = [
        concurrent_delivery_probe(working_copy.path).observations["effect_count"] for _ in range(5)
    ]
    assert observed == [2, 2, 2, 2, 2], f"non-deterministic reproduction: {observed}"


def test_higher_concurrency_still_duplicates(working_copy) -> None:
    result = concurrent_delivery_probe(working_copy.path, workers=4)
    assert result.observations["effect_count"] == 4


def test_sequential_redelivery_does_not_duplicate(working_copy) -> None:
    """The falsifier.

    Without this the investigation could accept "there is no duplicate check" —
    plausible, wrong, and it happens to motivate a working patch anyway.
    """
    result = sequential_redelivery_probe(working_copy.path)
    assert result.exit_code == 0
    assert result.observations["raw_result_rows"] == 1
    assert result.observations["effect_count"] == 1
    assert result.observations["duplicate_processing"] is False


def test_delivery_is_declared_at_least_once(working_copy) -> None:
    """Which falsifies "the queue is broken": redelivery is contractual."""
    result = delivery_contract_probe(working_copy.path)
    assert result.observations["declared_delivery_model"] == "at-least-once"
    assert result.observations["redelivery_is_contractual"] is True


def test_visible_suite_fails_on_the_known_bad_fixture(working_copy) -> None:
    """The reported symptom is real and visible before any patch."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests_visible", "-q", "-p", "no:cacheprovider"],
        cwd=str(working_copy.path),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode != 0
    assert "test_concurrent_delivery_yields_one_result" in result.stdout


def test_hidden_suite_fails_on_the_known_bad_fixture(tmp_path: Path) -> None:
    copy = create_working_copy(destination_root=tmp_path, include_hidden_tests=True)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests_hidden", "-q", "-p", "no:cacheprovider"],
            cwd=str(copy.path),
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        assert result.returncode != 0
    finally:
        copy.cleanup()


def test_the_fixture_declares_its_invariants() -> None:
    invariants = (FIXTURE_ROOT / "INVARIANTS.md").read_text(encoding="utf-8")
    assert "One logical job identifier may produce at most one committed processing" in invariants
    assert "at-least-once" in invariants.lower()
