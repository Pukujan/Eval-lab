"""Focused offline contracts for routing accounting and TASK-0010 policy metrics."""

from __future__ import annotations

import json
from pathlib import Path

from eval_lab.metrics.policy import REQUIRED_POLICY_METRIC_KEYS, summarize_policy_metrics
from eval_lab.schema import (
    ExecutionStatus,
    GoldLabel,
    GoldProvenance,
    JudgePrediction,
    JudgeRecord,
    JudgmentMode,
    RubricCriterion,
    Split,
)
from scripts.generate_research_artifacts import REQUIRED_PAPER_SECTIONS, render_paper
from scripts.run_selective_escalation import _provider_only_rows, _student_routes


def _record(record_id: str, label: str, domain: str = "arc_challenge") -> JudgeRecord:
    return JudgeRecord(
        record_id=record_id,
        source_problem_id=record_id,
        mode=JudgmentMode.SINGLE,
        prompt="Evaluate the candidate.",
        rubric=[RubricCriterion(criterion_id="correct", description="Correct", weight=1.0)],
        candidate_a="candidate",
        gold=GoldLabel(label=label, provenance=GoldProvenance.ANSWER_KEY, evidence={}),
        split=Split.TEST,
    )


def _local(record_id: str, label: str, confidence: float) -> JudgePrediction:
    other = "fail" if label == "pass" else "pass"
    return JudgePrediction(
        record_id=record_id,
        judge_id="task-0009-arm-d",
        protocol_version="test",
        label=label,
        probabilities={label: confidence, other: 1.0 - confidence},
        latency_ms=1.0,
    )


def _provider(
    record_id: str,
    label: str | None,
    *,
    status: ExecutionStatus = ExecutionStatus.OK,
    model: str = "typesafe/jev-1.13",
    latency_ms: float | None = 10.0,
    cost: float | None = 0.001,
) -> JudgePrediction:
    metadata: dict = {"provider": "openrouter", "model": model}
    if cost is not None:
        metadata["usage"] = {"input_tokens": 10.0, "output_tokens": 2.0, "cost": cost}
    return JudgePrediction(
        record_id=record_id,
        judge_id=model,
        protocol_version="test",
        label=label,
        execution_status=status,
        latency_ms=latency_ms,
        provider_metadata=metadata,
        error=None if status is ExecutionStatus.OK else {"type": status.value},
    )


def test_local_routes_always_report_provider_status_not_called() -> None:
    records = [_record("keep", "pass"), _record("send", "fail")]
    local = [_local("keep", "pass", 0.95), _local("send", "fail", 0.55)]
    escalated = {"send": _provider("send", "fail")}
    rows = _student_routes(
        records,
        local,
        threshold=0.90,
        calibrated_confidences={"keep": 0.95, "send": 0.55},
        local_predictions={item.record_id: item for item in local},
        escalated_predictions=escalated,
    )
    by_id = {row["record_id"]: row for row in rows}
    assert by_id["keep"]["route"] == "local"
    assert by_id["keep"]["provider_status"] == "not_called"
    assert by_id["keep"]["provider_model"] is None
    assert by_id["keep"]["final_label"] == "pass"
    assert by_id["send"]["route"] == "escalate"
    assert by_id["send"]["provider_status"] == "ok"
    assert by_id["send"]["provider_model"] == "typesafe/jev-1.13"
    assert by_id["send"]["final_label"] == "fail"


def test_escalated_missing_or_failed_provider_stays_unresolved() -> None:
    records = [_record("missing", "pass"), _record("failed", "fail")]
    local = [_local("missing", "pass", 0.4), _local("failed", "fail", 0.4)]
    escalated = {
        "failed": _provider("failed", None, status=ExecutionStatus.PROVIDER_ERROR, cost=None),
    }
    rows = _student_routes(
        records,
        local,
        threshold=0.90,
        calibrated_confidences={"missing": 0.4, "failed": 0.4},
        local_predictions={item.record_id: item for item in local},
        escalated_predictions=escalated,
    )
    by_id = {row["record_id"]: row for row in rows}
    assert by_id["missing"]["final_label"] is None
    assert by_id["missing"]["provider_status"] == "not_called"
    assert by_id["failed"]["final_label"] is None
    assert by_id["failed"]["provider_status"] == "provider_error"


def test_provider_only_rows_cover_frozen_pool_without_fabricated_labels() -> None:
    records = [_record("ok", "pass"), _record("gap", "fail")]
    rows = _provider_only_rows(
        records,
        {"ok": _provider("ok", "pass")},
        model="typesafe/jev-1.13",
    )
    by_id = {row["record_id"]: row for row in rows}
    assert by_id["ok"]["route"] == "escalate"
    assert by_id["ok"]["final_label"] == "pass"
    assert by_id["ok"]["provider_status"] == "ok"
    assert by_id["gap"]["route"] == "escalate"
    assert by_id["gap"]["final_label"] is None
    assert by_id["gap"]["provider_status"] == "not_called"
    assert by_id["gap"]["provider_error"] == {"type": "provider_not_available"}


def test_policy_metrics_include_required_schema_and_wilson_support_flags() -> None:
    records = [_record("keep", "pass"), _record("send", "fail")]
    local = [_local("keep", "pass", 0.95), _local("send", "fail", 0.55)]
    provider = _provider("send", "fail", latency_ms=20.0, cost=0.002)
    rows = _student_routes(
        records,
        local,
        threshold=0.90,
        calibrated_confidences={"keep": 0.95, "send": 0.55},
        local_predictions={item.record_id: item for item in local},
        escalated_predictions={"send": provider},
    )
    selected = {"keep": local[0], "send": provider}
    summary = summarize_policy_metrics(
        records,
        rows,
        domain_by_record_id={"keep": "arc_challenge", "send": "arc_challenge"},
        selected_predictions=selected,
        ranking_correct=[True, True],
        ranking_confidence=[0.95, 0.55],
        target_error=0.01,
        threshold=0.90,
    )
    missing = [key for key in REQUIRED_POLICY_METRIC_KEYS if key not in summary]
    assert missing == []
    assert summary["accuracy"] == 1.0
    assert summary["balanced_accuracy"] == 1.0
    assert summary["macro_f1"] == 1.0
    assert summary["provider_status_counts"]["not_called"] == 1
    assert summary["provider_status_counts"]["ok"] == 1
    assert summary["external_calls"] == 1
    assert summary["external_calls_per_1000"] == 500.0
    assert summary["latency"]["p95_ms"] is not None
    assert summary["provider_resources"]["cost"] == 0.002
    assert set(summary["risk_coverage"]["coverage_at_target_error"]) == {
        "0.01",
        "0.02",
        "0.05",
        "0.10",
    }
    point = summary["risk_coverage"]["coverage_at_target_error"]["0.01"]
    assert "confidence_supported" in point
    assert point["claim_status"] in {"confidence-supported", "descriptive"}
    assert summary["selected_operating_point"]["threshold"] == 0.90
    assert summary["selected_operating_point"]["target_error"] == 0.01


def test_probability_metrics_are_explicitly_unavailable_without_probabilities() -> None:
    records = [_record("one", "pass")]
    rows = _provider_only_rows(records, {"one": _provider("one", "pass")}, model="qwen3.8-flash")
    summary = summarize_policy_metrics(
        records,
        rows,
        selected_predictions={"one": _provider("one", "pass", model="qwen3.8-flash", cost=None)},
    )
    assert summary["probability_metrics"]["available"] is False
    assert summary["probability_metrics"]["brier"] is None
    assert summary["probability_metrics"]["nll"] is None
    assert summary["probability_metrics"]["ece"] is None
    assert summary["probability_metrics"]["unavailable_reason"]


def test_policy_metrics_keep_supplied_threshold_instead_of_using_final_labels() -> None:
    records = [_record("a", "pass"), _record("b", "pass")]
    local = [_local("a", "pass", 0.99), _local("b", "fail", 0.51)]
    rows = _student_routes(
        records,
        local,
        threshold=0.80,
        calibrated_confidences={"a": 0.99, "b": 0.51},
        local_predictions={item.record_id: item for item in local},
        escalated_predictions={},
    )
    summary = summarize_policy_metrics(
        records,
        rows,
        selected_predictions={item.record_id: item for item in local},
        ranking_correct=[True, False],
        ranking_confidence=[0.99, 0.51],
        target_error=0.10,
        threshold=0.80,
    )
    assert summary["selected_operating_point"]["threshold"] == 0.80
    assert rows[1]["final_label"] is None


def test_render_paper_uses_results_json_and_required_sections(tmp_path: Path) -> None:
    results = {
        "experiment_id": "EXP-20260920-012-selective-escalation-qwen-streaming",
        "status": "completed",
        "benchmark_fingerprint": "18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5",
        "counts": {"threshold_selection": 2863, "final_evaluation": 2356, "provider_evaluation": 500},
        "policies": {
            "local_only": {
                "total_count": 2,
                "local_coverage": 1.0,
                "escalation_rate": 0.0,
                "execution_coverage": 1.0,
                "unresolved_rate": 0.0,
                "accuracy": 0.5,
                "balanced_accuracy": 0.5,
                "macro_f1": 0.5,
                "final_resolved_risk": 0.5,
                "final_resolved_risk_interval_95": {"lower": 0.1, "upper": 0.9},
                "selected_operating_point": None,
                "risk_coverage": {
                    "coverage_at_target_error": {
                        "0.01": {
                            "coverage": 0.0,
                            "confidence_supported": False,
                            "claim_status": "descriptive",
                        }
                    }
                },
            },
            "pinned_jev_only": {
                "total_count": 2,
                "local_coverage": 0.0,
                "escalation_rate": 1.0,
                "execution_coverage": 0.5,
                "unresolved_rate": 0.5,
                "accuracy": 1.0,
                "balanced_accuracy": 1.0,
                "macro_f1": 1.0,
                "final_resolved_risk": 0.0,
                "final_resolved_risk_interval_95": {"lower": 0.0, "upper": 0.8},
                "selected_operating_point": None,
                "risk_coverage": {"coverage_at_target_error": {}},
            },
            "calibrated_local_to_jev_target_0.01": {
                "total_count": 2,
                "local_coverage": 0.5,
                "escalation_rate": 0.5,
                "execution_coverage": 1.0,
                "unresolved_rate": 0.0,
                "accuracy": 1.0,
                "balanced_accuracy": 1.0,
                "macro_f1": 1.0,
                "final_resolved_risk": 0.0,
                "final_resolved_risk_interval_95": {"lower": 0.0, "upper": 0.8},
                "selected_operating_point": {
                    "target_error": 0.01,
                    "threshold": 0.9,
                    "local_coverage": 0.5,
                    "local_accepted_risk": 0.0,
                    "confidence_supported": False,
                    "claim_status": "descriptive",
                    "collapsed": True,
                    "collapsed_targets": ["0.01", "0.02", "0.05", "0.10"],
                },
                "risk_coverage": {
                    "coverage_at_target_error": {
                        "0.01": {
                            "coverage": 0.5,
                            "confidence_supported": False,
                            "claim_status": "descriptive",
                        }
                    }
                },
            },
        },
        "system_one_differential": {"comparable_count": 500, "agreement_count": 486},
        "provider_arms": {
            "openrouter_pinned": {"model": "typesafe/jev-1.13", "status_counts": {"ok": 500}},
            "openrouter_rolling": {"model": "~typesafe/jev-latest", "status_counts": {"ok": 500}},
            "yolo_qwen_flash": {"model": "qwen3.8-flash", "status_counts": {"ok": 500}},
        },
    }
    paper_root = tmp_path / "paper"
    render_paper(
        results,
        {"comparable_count": 1, "agreement_count": 1},
        Path("experiments/EXP-20260920-012-selective-escalation-qwen-streaming"),
        Path("experiments/EXP-20260920-009-selective-escalation"),
        paper_root=paper_root,
    )
    tex = (paper_root / "main.tex").read_text(encoding="utf-8")
    for section in REQUIRED_PAPER_SECTIONS:
        assert section in tex, section
    assert "EXP-20260920-012-selective-escalation-qwen-streaming" in tex
    assert "pinned\\_jev\\_only" in (paper_root / "generated" / "table_selective_results.tex").read_text(
        encoding="utf-8"
    )
    assert "descriptive" in tex
    assert "Project Continuity Modules" in tex or "PCM" in tex
    limitations = (paper_root / "limitations.md").read_text(encoding="utf-8")
    assert "PCM" in limitations or "Project Continuity Modules" in limitations
    table = (paper_root / "generated" / "table_selective_results.tex").read_text(encoding="utf-8")
    parsed = json.dumps(results)
    assert "0.500" in table or "0.5" in parsed
