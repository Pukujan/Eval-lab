from __future__ import annotations

from pathlib import Path

from eval_lab.schema import GoldLabel, JudgeRecord, JudgmentMode, RubricCriterion, Split
from scripts import run_grok_protocol_ablation as ablation
from scripts.run_grok_protocol_ablation import (
    VARIANTS,
    build_prompt,
    canonicalize_label,
    output_schema,
    selection_score,
)


def _single() -> JudgeRecord:
    return JudgeRecord(
        record_id="r-single",
        source_problem_id="p-single",
        mode=JudgmentMode.SINGLE,
        prompt="Question? Choices: A) one B) two",
        rubric=[
            RubricCriterion(
                criterion_id="c",
                description="The candidate selects the answer-key choice.",
                aggregation_rule="all",
                weight=1.0,
            )
        ],
        candidate_a="A) one",
        gold=GoldLabel(label="pass", provenance="answer_key", evidence={}),
        split=Split.CALIBRATION,
    )


def _pairwise() -> JudgeRecord:
    return _single().model_copy(
        update={
            "record_id": "r-pair",
            "source_problem_id": "p-pair",
            "mode": JudgmentMode.PAIRWISE,
            "candidate_b": "B) two",
            "gold": {"label": "A", "provenance": "deterministic_verifier", "evidence": {}},
        }
    )


def test_all_variants_have_declared_prompt_and_schema_behavior() -> None:
    assert set(VARIANTS) == {
        "typed_schema",
        "explicit_schema",
        "semantic_schema",
        "explicit_no_schema",
    }
    for variant in VARIANTS:
        assert build_prompt(_single(), variant)
        if variant == "explicit_no_schema":
            assert output_schema(_single(), variant) is None
        else:
            assert '"label"' in output_schema(_single(), variant)


def test_semantic_labels_map_without_ambiguous_fallback() -> None:
    assert canonicalize_label("CORRECT", _single(), "semantic_schema") == "pass"
    assert canonicalize_label("INCORRECT", _single(), "semantic_schema") == "fail"
    assert canonicalize_label("A_BETTER", _pairwise(), "semantic_schema") == "A"
    assert canonicalize_label("B_BETTER", _pairwise(), "semantic_schema") == "B"
    assert canonicalize_label("EQUIVALENT", _pairwise(), "semantic_schema") == "TIE"
    assert canonicalize_label("TIE", _pairwise(), "typed_schema") == "TIE"
    assert canonicalize_label("maybe", _single(), "semantic_schema") is None


def test_selection_score_is_mode_balanced() -> None:
    assert selection_score({"single": {"accuracy": 1.0}, "pairwise": {"accuracy": 0.5}}) == 0.75


def test_ablation_prompt_is_passed_by_file_not_argv(monkeypatch) -> None:
    record = _single()
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = list(command)
        prompt_path = Path(command[command.index("--prompt-file") + 1])
        captured["existed"] = prompt_path.exists()
        captured["prompt"] = prompt_path.read_text(encoding="utf-8")
        captured["path"] = prompt_path
        return 0, '{"structuredOutput":{"label":"pass"}}', "", False, 1

    monkeypatch.setattr(ablation, "_run_streaming_process", fake_run)
    prediction = ablation.run_one(
        record,
        arm_id="grok_46",
        model="grok-4.6",
        variant="typed_schema",
        environment={"GROK_EXE": "grok"},
        timeout=10.0,
    )
    prompt = build_prompt(record, "typed_schema")
    command = captured["command"]
    assert "\n" in prompt
    assert "--prompt-file" in command
    assert not any(token.startswith("--single") for token in command)
    assert all(prompt not in token for token in command)
    assert captured["existed"] is True
    assert captured["prompt"] == prompt
    assert prediction.label == "pass"
    assert not Path(captured["path"]).exists()
