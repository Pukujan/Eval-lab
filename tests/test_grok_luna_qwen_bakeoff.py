from __future__ import annotations

import json
from pathlib import Path

import httpx

from eval_lab.schema import GoldLabel, GoldProvenance, JudgeRecord, JudgmentMode, Split
from scripts import run_grok_luna_qwen_bakeoff as runner
from scripts.run_grok_luna_qwen_bakeoff import (
    ARMS,
    _differential,
    _grok_json_schema,
    _qwen_stream_response,
    _wilson,
    parse_label,
)


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


def test_grok_schema_keeps_record_legal_labels() -> None:
    schema = _grok_json_schema(_record())
    assert '"enum":["fail","pass"]' in schema
    assert '"additionalProperties":false' in schema


def test_grok_47_is_a_separate_direct_cli_arm() -> None:
    assert ARMS["grok"]["requested_model"] == "grok-4.6"
    assert ARMS["grok_47"]["requested_model"] == "grok-4.7"
    assert ARMS["grok"]["route"] == ARMS["grok_47"]["route"]


def test_grok_prompt_is_passed_by_file_not_argv(monkeypatch) -> None:
    """The multi-line prompt must never travel through argv.

    On Windows `grok` resolves to `grok.CMD`, and cmd.exe truncates an argument
    at an embedded newline; an inline `--single=<prompt>` therefore loses the
    record payload and the model collapses to `fail`/`TIE`. The prompt must go
    through `--prompt-file` and the temp file must be cleaned up.
    """

    record = _record()
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = list(command)
        prompt_path = Path(command[command.index("--prompt-file") + 1])
        captured["existed"] = prompt_path.exists()
        captured["prompt"] = prompt_path.read_text(encoding="utf-8")
        captured["path"] = prompt_path
        return 0, '{"structuredOutput":{"label":"pass"}}', "", False, 1

    monkeypatch.setattr(runner, "_run_streaming_process", fake_run)

    prediction = runner._run_grok_build_one(
        record,
        arm_id="grok",
        model="grok-4.6",
        route="direct_grok_build_cli_subscription",
        environment={},
        timeout=10.0,
    )

    prompt = runner._prompt(record)
    command = captured["command"]
    assert "\n" in prompt  # the defect only manifests because the prompt is multi-line
    assert "--prompt-file" in command
    assert not any(token.startswith("--single") for token in command)
    assert all(prompt not in token for token in command)
    assert captured["existed"] is True
    assert captured["prompt"] == prompt
    assert prediction.label == "pass"
    assert not Path(captured["path"]).exists()  # temp prompt file removed in finally


def test_qwen_sse_stream_reassembles_typed_content() -> None:
    body = "\n\n".join(
        [
            "data: "
            + json.dumps(
                {"model": "qwen3.8-flash", "choices": [{"delta": {"content": '{"label":"'}}]}
            ),
            "data: "
            + json.dumps({"model": "qwen3.8-flash", "choices": [{"delta": {"content": 'pass"}'}}]}),
            'data: {"usage":{"prompt_tokens":3,"completion_tokens":2}}',
            "data: [DONE]",
        ]
    ).encode()
    response = httpx.Response(
        200, content=body, request=httpx.Request("POST", "https://example.test")
    )
    content, surfaced, usage, event_count = _qwen_stream_response(response, record=_record())
    assert content == '{"label":"pass"}'
    assert surfaced == ["qwen3.8-flash"]
    assert usage == {"prompt_tokens": 3, "completion_tokens": 2}
    assert event_count == 3
