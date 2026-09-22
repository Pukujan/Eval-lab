from __future__ import annotations

from eval_lab.schema import JudgeRecord, JudgmentMode
from scripts.run_inferhub_arm import parse_label, parse_sse


def _single() -> JudgeRecord:
    return JudgeRecord.model_validate(
        {
            "record_id": "single-1",
            "source_problem_id": "source-1",
            "mode": "single",
            "prompt": "Is this correct?",
            "rubric": [{"criterion_id": "c1", "description": "Correct", "weight": 1}],
            "candidate_a": "yes",
            "gold": {"label": "pass", "provenance": "answer_key", "evidence": {"answer": "pass"}},
            "split": "test",
        }
    )


def test_parse_label_accepts_json_and_rejects_unrelated_words() -> None:
    record = _single()
    assert parse_label('{"label":"pass"}', record) == "pass"
    assert parse_label("The final label is fail.", record) == "fail"
    assert parse_label('{"label":"maybe"}', record) is None


def test_parse_sse_collects_content_model_and_usage() -> None:
    content, models, usage = parse_sse(
        [
            'data: {"model":"zai/glm-5.3-flash","choices":[{"delta":{"content":"{\\"label\\":\\"pass\\"}"}}]}',
            'data: {"choices":[],"usage":{"prompt_tokens":12,"completion_tokens":4,"total_tokens":16,"cost":0.00001}}',
            "data: [DONE]",
        ]
    )
    assert content == '{"label":"pass"}'
    assert models == ["zai/glm-5.3-flash"]
    assert usage["total_tokens"] == 16


def test_pairwise_label_uses_uppercase_legal_set() -> None:
    record = _single().model_copy(update={"record_id": "pair-1", "mode": JudgmentMode.PAIRWISE, "candidate_b": "no"})
    assert parse_label('{"label":"B"}', record) == "B"
