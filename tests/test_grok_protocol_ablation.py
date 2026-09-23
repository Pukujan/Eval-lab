from __future__ import annotations

from eval_lab.schema import GoldLabel, JudgeRecord, JudgmentMode, RubricCriterion, Split
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
        rubric=[RubricCriterion(criterion_id="c", description="The candidate selects the answer-key choice.", aggregation_rule="all", weight=1.0)],
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
    assert set(VARIANTS) == {"typed_schema", "explicit_schema", "semantic_schema", "explicit_no_schema"}
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
