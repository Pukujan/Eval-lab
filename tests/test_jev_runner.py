import asyncio
import json
from typing import Any, Self

import pytest

from eval_lab import jev
from eval_lab.datasets.synthetic import generate_synthetic_fixtures
from eval_lab.schema import (
    GoldLabel,
    GoldProvenance,
    JudgeRecord,
    JudgmentMode,
    RubricCriterion,
    Split,
)


class FakeResponse:
    def __init__(self, status_code: int, payload: Any = None, headers: dict[str, str] | None = None) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}

    def json(self) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeAsyncClient:
    response = FakeResponse(200, {"label": "pass", "probabilities": {"pass": 0.8, "fail": 0.2}})
    last_json: dict[str, Any] | None = None
    expected_key = "test-key"

    def __init__(self, **_: Any) -> None:
        pass

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, _url: str, *, headers: dict[str, str], json: dict[str, Any]) -> FakeResponse:
        self.__class__.last_json = json
        assert headers["Authorization"] == f"Bearer {self.expected_key}"
        return self.response


def test_direct_request_pins_free_model_and_normalizes_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jev.httpx, "AsyncClient", FakeAsyncClient)
    record = generate_synthetic_fixtures().single_records[0]

    prediction = asyncio.run(jev.run_jev([record], api_key="test-key"))[0]

    assert FakeAsyncClient.last_json is not None
    assert FakeAsyncClient.last_json["model"] == "jev-1.13-free"
    assert prediction.label == "pass"
    assert prediction.probabilities == {"pass": 0.8, "fail": 0.2}
    assert prediction.provider_metadata["model"] == "jev-1.13-free"


def test_paid_model_is_rejected_without_fallback() -> None:
    with pytest.raises(ValueError, match="no paid fallback"):
        asyncio.run(
            jev.evaluate_jev(
                state="candidate",
                questions={},
                model="jev-1.13",
                api_key="test-key",
            )
        )


def test_429_maps_to_rate_limited_and_preserves_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    class RateLimitedClient(FakeAsyncClient):
        response = FakeResponse(429, {"error": "limited"}, {"Retry-After": "120"})

    monkeypatch.setattr(jev.httpx, "AsyncClient", RateLimitedClient)
    record = generate_synthetic_fixtures().single_records[0]
    prediction = asyncio.run(jev.run_jev([record], api_key="test-key"))[0]

    assert prediction.execution_status.value == "rate_limited"
    assert prediction.label is None
    assert prediction.error == {
        "type": "rate_limited",
        "status_code": 429,
        "retry_after_seconds": 120.0,
    }


def test_5xx_maps_to_provider_error_without_response_body(monkeypatch: pytest.MonkeyPatch) -> None:
    class ServerErrorClient(FakeAsyncClient):
        response = FakeResponse(503, {"secret": "should-not-serialize"})
        expected_key = "secret-key"

    monkeypatch.setattr(jev.httpx, "AsyncClient", ServerErrorClient)
    record = generate_synthetic_fixtures().single_records[0]
    prediction = asyncio.run(jev.run_jev([record], api_key="secret-key"))[0]

    serialized = prediction.model_dump_json()
    assert prediction.execution_status.value == "provider_error"
    assert prediction.label is None
    assert "secret" not in serialized
    assert "secret-key" not in serialized


def test_malformed_provider_payload_maps_to_parse_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class MalformedClient(FakeAsyncClient):
        response = FakeResponse(200, ValueError("bad json"))

    monkeypatch.setattr(jev.httpx, "AsyncClient", MalformedClient)
    record = generate_synthetic_fixtures().single_records[0]
    prediction = asyncio.run(jev.run_jev([record], api_key="test-key"))[0]
    assert prediction.execution_status.value == "parse_error"
    assert prediction.label is None


def test_atomic_aggregation_is_deterministic_and_retains_probabilities() -> None:
    record = JudgeRecord(
        record_id="atomic-1",
        source_problem_id="problem-1",
        mode=JudgmentMode.SINGLE,
        prompt="Answer.",
        rubric=[
            RubricCriterion(criterion_id="first", description="First criterion"),
            RubricCriterion(criterion_id="second", description="Second criterion"),
        ],
        candidate_a="candidate",
        gold=GoldLabel(
            label="pass",
            provenance=GoldProvenance.DETERMINISTIC_VERIFIER,
            evidence={"source": "test"},
        ),
        split=Split.TEST,
    )
    response = {
        "criteria": {
            "first": {"label": "pass", "probabilities": {"pass": 0.9, "fail": 0.1}},
            "second": {"label": "fail", "probabilities": {"pass": 0.2, "fail": 0.8}},
        }
    }
    prediction = jev.normalize_atomic_response(response, record, latency_ms=12.5)
    assert prediction.label == "fail"
    assert prediction.probabilities == {"pass": 0.55, "fail": 0.45}
    assert prediction.provider_metadata["criterion_labels"] == {"first": "pass", "second": "fail"}


def test_pairwise_class_order_is_stable() -> None:
    record = generate_synthetic_fixtures().pairwise_records[0]
    prediction = jev.normalize_direct_response(
        {"verdict": "B", "probabilities": {"A": 0.1, "B": 0.8, "TIE": 0.1}},
        record,
    )
    assert prediction.label == "B"
    assert list(prediction.probabilities or {}) == ["A", "B", "TIE"]


def test_jsonl_writer_emits_only_normalized_predictions(tmp_path: Any) -> None:
    record = generate_synthetic_fixtures().single_records[0]
    prediction = jev.normalize_direct_response(
        {"label": "pass", "probabilities": {"pass": 1.0, "fail": 0.0}},
        record,
    )
    output = tmp_path / "predictions.jsonl"
    jev.write_predictions_jsonl([prediction], output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["record_id"] == record.record_id
    assert "raw_response" not in payload
