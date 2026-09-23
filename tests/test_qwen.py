import pytest

from eval_lab.judges.qwen import (
    QwenRuntimeConfig,
    format_judge_prompt,
    format_system_one_judge_prompt,
    legal_labels,
    softmax_scores,
)
from eval_lab.schema import (
    GoldLabel,
    GoldProvenance,
    JudgeRecord,
    JudgmentMode,
    RubricCriterion,
    Split,
)


def _record(mode: JudgmentMode) -> JudgeRecord:
    return JudgeRecord(
        record_id="record-1",
        source_problem_id="source-1",
        mode=mode,
        prompt="Select the correct candidate.",
        rubric=[RubricCriterion(criterion_id="correct", description="Prefer the correct answer.")],
        candidate_a="right",
        candidate_b="wrong" if mode is JudgmentMode.PAIRWISE else None,
        gold=GoldLabel(label="A" if mode is JudgmentMode.PAIRWISE else "pass", provenance=GoldProvenance.ANSWER_KEY, evidence={}),
        split=Split.TEST,
    )


def test_legal_labels_and_prompt_are_canonical() -> None:
    assert legal_labels(_record(JudgmentMode.SINGLE)) == ["pass", "fail"]
    assert legal_labels(_record(JudgmentMode.PAIRWISE)) == ["A", "B", "TIE"]
    prompt = format_judge_prompt(_record(JudgmentMode.PAIRWISE))
    assert "Candidate A:" in prompt
    assert "Candidate B:" in prompt
    assert "Verdict:" in prompt


def test_system_one_prompt_is_typed_and_declared() -> None:
    prompt = format_judge_prompt(
        _record(JudgmentMode.SINGLE),
        prompt_version="eval-lab-system-one-local-v1",
    )
    assert '"state"' in prompt
    assert '"questions"' in prompt
    assert "Verdict:" in prompt


def test_system_one_prompt_builder_matches_direct_payload_shape() -> None:
    prompt = format_system_one_judge_prompt(_record(JudgmentMode.PAIRWISE))
    assert '"criteria"' in prompt
    assert "A, B, TIE" in prompt


def test_softmax_preserves_order_and_normalizes() -> None:
    probabilities = softmax_scores({"A": -1.0, "B": -2.0, "TIE": -3.0})

    assert sum(probabilities.values()) == pytest.approx(1.0)
    assert probabilities["A"] > probabilities["B"] > probabilities["TIE"]


def test_runtime_config_requires_positive_context_cap() -> None:
    with pytest.raises(ValueError, match="context_cap"):
        QwenRuntimeConfig(context_cap=0)


def test_runtime_config_records_prompt_version() -> None:
    config = QwenRuntimeConfig(prompt_version="eval-lab-system-one-local-v1")
    assert config.prompt_version == "eval-lab-system-one-local-v1"


def test_runtime_config_accepts_memory_safe_quantization_modes() -> None:
    assert QwenRuntimeConfig(quantization="4bit").quantization == "4bit"
    with pytest.raises(ValueError, match="quantization"):
        QwenRuntimeConfig(quantization="unsupported")


def test_runtime_config_validates_gpu_memory_fraction() -> None:
    assert QwenRuntimeConfig(gpu_memory_fraction=0.8).gpu_memory_fraction == 0.8
    with pytest.raises(ValueError, match="gpu_memory_fraction"):
        QwenRuntimeConfig(gpu_memory_fraction=1.1)

