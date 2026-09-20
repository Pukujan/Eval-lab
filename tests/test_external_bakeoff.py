from eval_lab.datasets.synthetic import generate_synthetic_fixtures
from eval_lab.schema import ExecutionStatus, JudgePrediction
from scripts.run_external_bakeoff import _coverage, _parse_label


def test_external_label_parser_uses_legal_class_set() -> None:
    records = generate_synthetic_fixtures().records
    single = next(record for record in records if record.mode.value == "single")
    pairwise = next(record for record in records if record.mode.value == "pairwise")

    assert _parse_label('{"label":"PASS"}', single) == "pass"
    assert _parse_label('{"label":"TIE"}', pairwise) == "TIE"
    assert _parse_label('{"label":"maybe"}', single) is None


def test_external_coverage_retains_failures_separately() -> None:
    predictions = [
        JudgePrediction(
            record_id="r1",
            judge_id="provider/model",
            protocol_version="external-forced-choice-v1",
            label="pass",
            execution_status=ExecutionStatus.OK,
        ),
        JudgePrediction(
            record_id="r2",
            judge_id="provider/model",
            protocol_version="external-forced-choice-v1",
            execution_status=ExecutionStatus.RATE_LIMITED,
        ),
        JudgePrediction(
            record_id="r3",
            judge_id="provider/model",
            protocol_version="external-forced-choice-v1",
            execution_status=ExecutionStatus.SKIPPED,
        ),
    ]

    coverage = _coverage(predictions)

    assert coverage["counts"] == {"ok": 1, "rate_limited": 1, "skipped": 1}
    assert coverage["record_ids"]["rate_limited"] == ["r2"]
