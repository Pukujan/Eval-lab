from __future__ import annotations

from eval_lab.schema import GoldLabel, GoldProvenance, JudgeRecord, JudgmentMode, Split
from scripts.run_grok_luna_qwen_bakeoff import _differential, _wilson, parse_label


def _record(record_id: str = "record-1") -> JudgeRecord:
    return JudgeRecord(
        record_id=record_id,
        source_problem_id="source-1",
        mode=JudgmentMode.SINGLE,
        prompt="Question",
        rubric=[{"criterion_id": "c1", "description": "Be correct."}],
        candidate_a="Answer",
        gold=GoldLabel(label="pass", provenance=GoldProvenance.ANSWER_KEY, evidence="key"),
        split=Split.TEST,
    )


def test_parse_label_reads_nested_event_json() -> None:
    assert parse_label('{"event":{"answer":{"label":"pass"}}}', _record()) == "pass"


def test_parse_label_rejects_illegal_label() -> None:
    assert parse_label('{"label":"maybe"}', _record()) is None


def test_wilson_interval_is_bounded() -> None:
    interval = _wilson(9, 10)
    assert interval is not None
    assert 0.0 <= interval["lower"] <= interval["upper"] <= 1.0


def test_differential_excludes_unresolved_records() -> None:
    record = _record()
    from eval_lab.schema import ExecutionStatus, JudgePrediction

    ok_a = JudgePrediction(
        record_id=record.record_id,
        judge_id="a",
        protocol_version="v1",
        label="pass",
        execution_status=ExecutionStatus.OK,
    )
    ok_b = ok_a.model_copy(update={"judge_id": "b", "label": "fail"})
    unresolved = ok_a.model_copy(
        update={"judge_id": "c", "label": None, "execution_status": ExecutionStatus.RATE_LIMITED}
    )
    result = _differential([record], {"a": [ok_a], "b": [ok_b], "c": [unresolved]})
    assert result["pairs"]["a__vs__b"]["agreement_count"] == 0
    assert result["pairs"]["a__vs__c"]["comparable_count"] == 0
