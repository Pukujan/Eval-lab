"""Promptfoo configuration tests.

Static checks always run. Actually executing the matrix needs the `promptfoo` CLI
and is skipped when it is absent.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

CONFIG_PATH = Path("evals/promptfoo/promptfooconfig.yaml")
BRIDGE_PATH = Path("evals/promptfoo/provider_bridge.py")


@pytest.fixture(scope="module")
def config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def test_at_least_three_mock_identities_are_compared(config: dict) -> None:
    providers = config["providers"]
    assert len(providers) >= 3
    models = {provider["config"]["model"] for provider in providers}
    assert models == {"mock-analyst", "mock-skeptic", "mock-minimalist"}


def test_identities_are_labelled_by_pseudonym_not_vendor(config: dict) -> None:
    for provider in config["providers"]:
        assert provider["label"].startswith("identity-")
        assert provider["config"]["pseudonym"].startswith("model-")


def test_all_providers_receive_identical_tasks(config: dict) -> None:
    """One prompt template, applied to every provider — otherwise it is not a
    comparison, it is three different experiments."""
    assert len(config["prompts"]) == 1
    assert len(config["tests"]) >= 1
    for test in config["tests"]:
        assert "assert" not in test, "per-test assertions would break comparability"


def test_assertions_are_deterministic(config: dict) -> None:
    asserts = config["defaultTest"]["assert"]
    kinds = {assertion["type"] for assertion in asserts}
    assert kinds <= {"is-json", "javascript"}, (
        f"non-deterministic assertion types present: {kinds - {'is-json', 'javascript'}}"
    )
    assert "is-json" in kinds


def test_no_model_graded_or_majority_vote_assertions(config: dict) -> None:
    """Agreement between models measures shared bias, not truth.

    Checks the assertion *types*, not the raw file: the config's prose explains
    why majority vote is not used, and a naive substring scan would flag the
    explanation as the offence.
    """
    forbidden_types = {
        "llm-rubric",
        "model-graded-closedqa",
        "model-graded-factuality",
        "factuality",
        "similar",
        "answer-relevance",
        "context-relevance",
        "select-best",
    }
    for assertion in config["defaultTest"]["assert"]:
        assert assertion["type"] not in forbidden_types, (
            f"model-graded assertion in use: {assertion['type']}"
        )
    for test in config["tests"]:
        for assertion in test.get("assert", []):
            assert assertion["type"] not in forbidden_types


def test_schema_diversity_and_evidence_assertions_exist(config: dict) -> None:
    body = json.dumps(config["defaultTest"]["assert"])
    assert "mechanism_class" in body, "no hypothesis-diversity assertion"
    assert "falsification_condition" in body, "no required-evidence-field assertion"
    assert "request_digest" in body, "no determinism assertion"
    assert "vendor identity" in body, "no blinding assertion"


def test_live_providers_are_optional_and_disabled(config: dict) -> None:
    raw = CONFIG_PATH.read_text(encoding="utf-8")
    assert "# Optional live providers" in raw
    for provider in config["providers"]:
        assert provider["config"]["model"].startswith("mock-")


def test_provider_bridge_implements_the_promptfoo_contract() -> None:
    source = BRIDGE_PATH.read_text(encoding="utf-8")
    assert "def call_api(prompt" in source
    assert "tokenUsage" in source, "latency/usage reporting is required"
    assert "latency_ms" in source


def test_bridge_returns_usage_and_latency_without_a_service() -> None:
    sys.path.insert(0, str(BRIDGE_PATH.parent.resolve()))
    from provider_bridge import call_api  # type: ignore[import-not-found]

    result = call_api(
        json.dumps({"task_type": "generate_hypotheses", "reported_symptom": "duplicates"}),
        {"config": {"model": "mock-analyst", "pseudonym": "model-abcdef12"}},
        {},
    )
    assert "error" not in result, result.get("error")
    assert result["tokenUsage"]["total"] > 0
    assert result["metadata"]["latency_ms"] >= 0
    body = json.loads(result["output"])
    assert len(body["hypotheses"]) >= 3


@pytest.mark.integration
def test_promptfoo_cli_validates_the_config() -> None:
    if shutil.which("promptfoo") is None:
        pytest.skip("promptfoo CLI not installed; config not validated by the tool here")

    result = subprocess.run(
        ["promptfoo", "validate", "-c", CONFIG_PATH.name],
        cwd=str(CONFIG_PATH.parent),
        capture_output=True,
        text=True,
        timeout=180,
        env={**os.environ, "PROMPTFOO_DISABLE_TELEMETRY": "1", "PROMPTFOO_DISABLE_UPDATE": "1"},
        check=False,
    )
    assert result.returncode == 0, f"promptfoo validate failed:\n{result.stdout}\n{result.stderr}"
