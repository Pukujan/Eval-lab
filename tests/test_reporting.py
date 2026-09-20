from eval_lab.reporting import build_report, render_report_markdown
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


def _record(record_id: str, domain: str, label: str) -> JudgeRecord:
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


def test_report_has_aggregate_domain_and_failure_reliability_sections() -> None:
    records = [_record("one", "math", "pass"), _record("two", "text", "fail")]
    predictions = [
        JudgePrediction(
            record_id="one",
            judge_id="fixture",
            protocol_version="test-v1",
            label="pass",
            probabilities={"pass": 0.9, "fail": 0.1},
            latency_ms=10,
        ),
        JudgePrediction(
            record_id="two",
            judge_id="fixture",
            protocol_version="test-v1",
            execution_status=ExecutionStatus.RATE_LIMITED,
            error={"type": "rate_limited"},
        ),
    ]

    report = build_report(records, predictions, domain_by_record_id={"one": "math", "two": "text"})
    markdown = render_report_markdown(report)

    assert report["total_count"] == 2
    assert report["successful_count"] == 1
    assert report["status_counts"] == {"ok": 1, "rate_limited": 1}
    assert report["aggregate"]["probability_metrics_available"] is True
    assert set(report["by_domain"]) == {"math"}
    assert "Aggregate metrics" in markdown


def test_report_marks_probability_metrics_unavailable() -> None:
    record = _record("one", "math", "pass")
    prediction = JudgePrediction(
        record_id="one",
        judge_id="fixture",
        protocol_version="test-v1",
        label="pass",
    )

    report = build_report([record], [prediction], domain_by_record_id={"one": "math"})

    assert report["probability_metrics"] == {
        "available": False,
        "unavailable_reason": "one or more successful predictions did not provide probabilities",
    }
