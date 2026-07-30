"""Model-adapter contract tests.

Asserts the properties the benchmark depends on: determinism, no credential
requirement, no silent fallback, and that the *resolved* model id is read back
rather than assumed.
"""

from __future__ import annotations

import json
import os

import pytest

from app.models.gateway import GatewayError, ModelGateway
from app.models.mock_provider import (
    MOCK_MODEL_NAMES,
    _build_content,
    _canonical_request_digest,
)
from app.models.registry import (
    ModelDescriptor,
    ModelResolutionError,
    build_default_registry,
)

TASK = {"task_type": "generate_hypotheses", "reported_symptom": "duplicates"}


@pytest.fixture
def gateway() -> ModelGateway:
    """In-process transport so the contract is testable with no service running."""
    return ModelGateway(
        registry=build_default_registry(),
        base_url="http://localhost:4000",
        api_key="not-needed",
        transport="in_process",
    )


def test_registry_exposes_three_deterministic_mocks() -> None:
    registry = build_default_registry()
    assert set(registry.mock_names) == set(MOCK_MODEL_NAMES)
    assert len(registry.mock_names) == 3
    assert registry.requires_no_credentials()
    assert registry.allow_fallback is False


def test_registry_supports_an_arbitrary_number_of_models() -> None:
    registry = build_default_registry()
    for index in range(25):
        registry.register(
            ModelDescriptor(
                logical_name=f"extra-{index}",
                gateway_model=f"extra-{index}",
                vendor="mock",
                endpoint="litellm-proxy",
            )
        )
    assert len(registry.logical_names) == 28


def test_unknown_model_is_an_error_not_a_substitution() -> None:
    with pytest.raises(ModelResolutionError):
        build_default_registry().get("no-such-model")


def test_fallback_between_named_models_is_refused() -> None:
    registry = build_default_registry()
    registry.verify_resolution("mock-analyst", "mock-analyst")
    with pytest.raises(ModelResolutionError, match="fallback is disabled"):
        registry.verify_resolution("mock-analyst", "mock-skeptic")


def test_retries_are_bounded_and_delegated_to_temporal() -> None:
    """LiteLLM's retry is zero so Temporal is the only retry layer."""
    for descriptor in build_default_registry().descriptors.values():
        assert descriptor.max_retries == 0


def test_invocation_is_deterministic(gateway: ModelGateway) -> None:
    first = gateway.invoke(pseudonym="model-11111111", logical_name="mock-analyst", task=TASK)
    second = gateway.invoke(pseudonym="model-11111111", logical_name="mock-analyst", task=TASK)
    assert first.content == second.content


def test_response_is_bound_to_the_request(gateway: ModelGateway) -> None:
    """A mock that ignores its input would make the whole benchmark meaningless."""
    first = gateway.invoke(pseudonym="model-11111111", logical_name="mock-analyst", task=TASK)
    other = gateway.invoke(
        pseudonym="model-11111111",
        logical_name="mock-analyst",
        task={**TASK, "reported_symptom": "something else entirely"},
    )
    assert (
        json.loads(first.content)["request_digest"] != json.loads(other.content)["request_digest"]
    )


def test_different_models_answer_differently(gateway: ModelGateway) -> None:
    contents = {
        name: gateway.invoke(pseudonym="model-22222222", logical_name=name, task=TASK).content
        for name in MOCK_MODEL_NAMES
    }
    assert len(set(contents.values())) == 3


def test_resolved_model_is_recorded(gateway: ModelGateway) -> None:
    invocation = gateway.invoke(pseudonym="model-33333333", logical_name="mock-skeptic", task=TASK)
    assert invocation.requested_model == "mock-skeptic"
    assert invocation.resolved_model.split("/")[-1] == "mock-skeptic"


def test_no_credentials_are_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """The mock path must work with every provider key removed from the env."""
    for key in list(os.environ):
        if key.endswith(("_API_KEY", "_TOKEN", "_SECRET")):
            monkeypatch.delenv(key, raising=False)

    gateway = ModelGateway(
        registry=build_default_registry(),
        base_url="http://localhost:4000",
        api_key="",
        transport="in_process",
    )
    invocation = gateway.invoke(pseudonym="model-44444444", logical_name="mock-analyst", task=TASK)
    assert invocation.parsed()["hypotheses"]


def test_prompt_naming_a_real_model_is_refused(gateway: ModelGateway) -> None:
    from app.models.blinding import IdentityLeakError

    with pytest.raises(IdentityLeakError):
        gateway.invoke(
            pseudonym="model-55555555",
            logical_name="mock-analyst",
            task={"task_type": "generate_hypotheses", "hint": "answer like claude would"},
        )


def test_non_json_response_is_a_gateway_error() -> None:
    from app.models.gateway import ModelInvocation

    invocation = ModelInvocation(
        pseudonym="model-66666666",
        requested_model="mock-analyst",
        resolved_model="mock-analyst",
        content="not json at all",
        prompt_tokens=1,
        completion_tokens=1,
        transport="in_process",
    )
    with pytest.raises(GatewayError):
        invocation.parsed()


def test_mock_handler_is_a_pure_function_of_model_and_messages() -> None:
    messages = [{"role": "user", "content": json.dumps(TASK)}]
    assert _build_content("mock-analyst", messages) == _build_content("mock-analyst", messages)
    assert _canonical_request_digest("mock-analyst", messages) == _canonical_request_digest(
        "mock-analyst", messages
    )
    assert _build_content("mock-analyst", messages) != _build_content("mock-skeptic", messages)


def test_mock_models_produce_the_required_hypothesis_fields(gateway: ModelGateway) -> None:
    required = {
        "causal_mechanism",
        "assumptions",
        "predicted_observations",
        "falsification_condition",
        "proposed_probe_id",
    }
    for name in MOCK_MODEL_NAMES:
        body = gateway.invoke(pseudonym="model-77777777", logical_name=name, task=TASK).parsed()
        assert len(body["hypotheses"]) >= 3
        for hypothesis in body["hypotheses"]:
            assert required.issubset(hypothesis), f"{name} omitted required fields"


def test_registry_records_no_vendor_for_mocks() -> None:
    for descriptor in build_default_registry().descriptors.values():
        assert descriptor.vendor == "mock"
