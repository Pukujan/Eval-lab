from __future__ import annotations

from eval_lab.schema import GoldLabel, GoldProvenance, JudgeRecord, JudgmentMode, Split
from scripts.run_multi_subscription_bakeoff import parse_label


def _record() -> JudgeRecord:
    return JudgeRecord(
        record_id="record-1",
        source_problem_id="source-1",
        mode=JudgmentMode.SINGLE,
        prompt="Question",
        rubric=[{"criterion_id": "c1", "description": "Be correct."}],
        candidate_a="Answer",
        gold=GoldLabel(label="pass", provenance=GoldProvenance.ANSWER_KEY, evidence="key"),
        split=Split.TEST,
    )


def test_parse_label_reads_nested_typed_json() -> None:
    assert parse_label('{"event":{"answer":{"label":"pass"}}}', _record()) == "pass"


def test_parse_label_uses_last_legal_token_for_cli_text() -> None:
    assert parse_label("OpenCode metadata\n{\"label\": \"fail\"}", _record()) == "fail"


def test_parse_label_rejects_illegal_label() -> None:
    assert parse_label('{"label":"maybe"}', _record()) is None
