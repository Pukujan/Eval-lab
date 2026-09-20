"""Offline contracts for selective routing, typed providers, and release identity."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from eval_lab.datasets.synthetic import generate_synthetic_fixtures
from eval_lab.escalation import (
    OPENROUTER_PINNED_MODEL,
    OPENROUTER_ROLLING_MODEL,
    Route,
    build_decision_spec,
    matched_random_record_ids,
    normalize_typed_response,
    route_prediction,
    select_threshold,
    wilson_interval,
)
from eval_lab.escalation.providers import run_openrouter_jev, run_yolo_qwen
from eval_lab.schema import ExecutionStatus, JudgePrediction, JudgmentMode, Split
from eval_lab.training import TextLogisticStudent


def _records() -> list:
    fixture = generate_synthetic_fixtures()
    return [record for record in fixture.records if record.mode is JudgmentMode.SINGLE and record.split is Split.TEST]


def _predictions(records: list) -> list[JudgePrediction]:
    return [
        JudgePrediction(
            record_id=record.record_id,
            judge_id="local-test",
            protocol_version="test",
            label=record.gold.label,
            probabilities={"pass": 0.9, "fail": 0.1}
            if record.gold.label == "pass"
            else {"pass": 0.1, "fail": 0.9},
        )
        for record in records
    ]


def test_threshold_boundary_is_local_and_selection_is_monotone() -> None:
    records = _records()[:4]
    predictions = _predictions(records)
    boundary = route_prediction(predictions[0], threshold=0.9)
    assert boundary.route is Route.LOCAL
    low = select_threshold(records, predictions, target_error=0.01)["selected"]["accepted_count"]
    high = select_threshold(records, predictions, target_error=0.10)["selected"]["accepted_count"]
    assert low <= high


def test_random_control_is_order_invariant_and_exactly_matched() -> None:
    ids = ["c", "a", "b", "a"]
    assert matched_random_record_ids(ids, 2, seed=7) == matched_random_record_ids(list(reversed(ids)), 2, seed=7)
    assert len(matched_random_record_ids(ids, 2, seed=7)) == 2


def test_wilson_interval_reports_low_error_uncertainty() -> None:
    interval = wilson_interval(0, 10)
    assert interval["lower"] == 0.0
    assert interval["upper"] > 0.0
    assert wilson_interval(0, 0)["upper"] == 1.0


def test_typed_spec_matches_provider_wire_contract() -> None:
    record = _records()[0]
    spec = build_decision_spec(record)
    payload = spec.provider_payload()
    assert payload["state"]
    assert payload["questions"]["verdict"]["type"] == "choice"
    assert list(payload["questions"]["verdict"]["criteria"]) == ["pass", "fail"]
    normalized = normalize_typed_response({"label": record.gold.label}, record, provider="mock", model="mock")
    assert normalized.label == record.gold.label
    openrouter = normalize_typed_response(
        {"answers": {"verdict": {"choice": record.gold.label, "probabilities": {"pass": 1, "fail": 0}}}},
        record,
        provider="openrouter",
        model=OPENROUTER_PINNED_MODEL,
    )
    assert openrouter.label == record.gold.label
    qwen = normalize_typed_response(
        {"choices": [{"message": {"content": '```json\n{"label": "pass"}\n```'}}]},
        record,
        provider="yolo-auto",
        model="qwen3.8-flash",
    )
    assert qwen.label == "pass"


def test_provider_adapters_keep_models_separate_and_fail_without_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    record = _records()[0]

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if request.url.host == "openrouter.ai":
            assert body["model"] in {OPENROUTER_PINNED_MODEL, OPENROUTER_ROLLING_MODEL}
            return httpx.Response(200, json={"label": "pass"})
        assert body["model"] == "qwen3.8-flash"
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"label":"pass"}'}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        pinned = run_openrouter_jev([record], api_key="test", client=client)
        rolling = run_openrouter_jev([record], model=OPENROUTER_ROLLING_MODEL, api_key="test", client=client)
        qwen = run_yolo_qwen([record], api_key="test", client=client)
    finally:
        client.close()
    assert pinned[0].judge_id == OPENROUTER_PINNED_MODEL
    assert rolling[0].judge_id == OPENROUTER_ROLLING_MODEL
    assert qwen[0].judge_id == "qwen3.8-flash"
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    skipped = run_openrouter_jev([record], api_key=None)
    assert skipped[0].execution_status is ExecutionStatus.SKIPPED
    assert skipped[0].label is None


def test_frozen_student_json_round_trips() -> None:
    artifact_path = Path("experiments/EXP-20260920-008-small-judge-training/artifacts/student_D.json")
    if not artifact_path.exists():
        pytest.skip("frozen TASK-0009 artifact is not present in this checkout")
    student = TextLogisticStudent.from_artifact(json.loads(artifact_path.read_text(encoding="utf-8")))
    records = _records()
    predictions = student.predict(records)
    assert len(predictions) == len(records)
    assert all(prediction.execution_status is ExecutionStatus.OK for prediction in predictions)
