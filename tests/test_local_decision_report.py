from __future__ import annotations

import json

import pytest

from scripts.report_local_decision_bakeoff import _percentile, summarize_predictions


def test_percentile_interpolates_between_sorted_values() -> None:
    assert _percentile([9.0, 1.0, 5.0], 0.5) == 5.0
    assert _percentile([1.0, 5.0], 0.95) == pytest.approx(4.8)


def test_summary_keeps_binary_and_pairwise_label_spaces_separate(tmp_path) -> None:
    records = [
        {"record_id": "single-1", "mode": "single", "gold": {"label": "pass"}},
        {"record_id": "pair-1", "mode": "pairwise", "gold": {"label": "B"}},
    ]
    predictions = [
        {
            "record_id": "single-1",
            "execution_status": "ok",
            "label": "pass",
            "probabilities": {"pass": 0.8, "fail": 0.2},
            "latency_ms": 20,
        },
        {
            "record_id": "pair-1",
            "execution_status": "ok",
            "label": "B",
            "probabilities": {"A": 0.1, "B": 0.7, "TIE": 0.2},
            "latency_ms": 40,
        },
    ]
    output = tmp_path / "predictions.jsonl"
    output.write_text("\n".join(json.dumps(row) for row in predictions) + "\n", encoding="utf-8")
    (tmp_path / "run-config.json").write_text(
        json.dumps({"runner_revision": "test-revision"}), encoding="utf-8"
    )

    result = summarize_predictions(
        records,
        predictions,
        prediction_path=output,
        mode_key="mode",
    )

    assert result["resolved_coverage"] == 1.0
    assert result["accuracy"] == 1.0
    assert result["by_mode"]["single"]["probability_metrics"]["brier"] == pytest.approx(0.08)
    assert result["by_mode"]["pairwise"]["probability_metrics"]["brier"] is not None
    assert result["runner_revision"] == "test-revision"


def test_summary_rejects_missing_or_extra_record_ids(tmp_path) -> None:
    output = tmp_path / "predictions.jsonl"
    output.write_text("{}\n", encoding="utf-8")
    (tmp_path / "run-config.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="prediction IDs do not match"):
        summarize_predictions(
            [{"record_id": "expected", "gold": {"label": "pass"}}],
            [{"record_id": "different", "execution_status": "ok"}],
            prediction_path=output,
            fixed_labels=["pass", "fail"],
        )
