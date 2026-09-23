from __future__ import annotations

import pytest

from eval_lab.datasets.humaneval import (
    assert_family_split_isolation,
    assign_humaneval_splits,
    canonicalize_humaneval_row,
    fingerprint_humaneval_rows,
    validate_humaneval_rows,
)
from eval_lab.schema import GoldProvenance, Split
from eval_lab.verifiers.humaneval import (
    HumanEvalStatus,
    build_humaneval_execution_result,
    verify_humaneval_execution,
)

ROW = {
    "task_id": "HumanEval/0",
    "prompt": "def add(a, b):\n    \"\"\"Return the sum.\"\"\"\n",
    "entry_point": "add",
    "canonical_solution": "    return a + b\n",
    "test": "def check(candidate):\n    assert candidate(1, 2) == 3\n",
}


def test_validation_rejects_duplicate_and_missing_source_ids() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_humaneval_rows([ROW, dict(ROW)])
    missing = dict(ROW)
    missing.pop("test")
    with pytest.raises(ValueError, match="test"):
        validate_humaneval_rows([missing])


def test_fingerprint_and_candidate_identity_are_byte_stable() -> None:
    reversed_row = {key: ROW[key] for key in reversed(list(ROW))}
    assert fingerprint_humaneval_rows([ROW]) == fingerprint_humaneval_rows([reversed_row])
    first = canonicalize_humaneval_row(
        ROW,
        "    return a + b\n",
        dataset_revision="abc123",
        split=Split.TEST,
    )
    second = canonicalize_humaneval_row(
        ROW,
        "    return a + b\n",
        dataset_revision="abc123",
        split=Split.TEST,
    )
    assert first == second
    assert len(first.record_id) == 64


def test_split_assignment_is_deterministic_and_family_safe() -> None:
    task_ids = [f"HumanEval/{index}" for index in range(10)]
    first = assign_humaneval_splits(task_ids, seed=7)
    second = assign_humaneval_splits(list(reversed(task_ids)), seed=7)
    assert first == second
    records = [
        canonicalize_humaneval_row(
            ROW,
            f"return {index}",
            dataset_revision="abc123",
            split=Split.DEV,
            candidate_slot=index,
        )
        for index in range(2)
    ]
    assert_family_split_isolation(records)
    records[1] = records[1].model_copy(update={"split": Split.TEST})
    with pytest.raises(ValueError, match="crosses split"):
        assert_family_split_isolation(records)


def test_judge_packet_does_not_include_hidden_tests() -> None:
    candidate = canonicalize_humaneval_row(
        ROW,
        "    return a - b\n",
        dataset_revision="abc123",
        split=Split.TEST,
    )
    gold = build_humaneval_execution_result(HumanEvalStatus.PASS).to_verifier_result().to_gold_label()
    record = candidate.to_judge_record(gold)
    assert ROW["test"] not in record.prompt
    assert ROW["canonical_solution"] not in record.prompt
    assert record.gold.provenance is GoldProvenance.DETERMINISTIC_VERIFIER


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (HumanEvalStatus.PASS, True),
        (HumanEvalStatus.TEST_FAILURE, False),
        (HumanEvalStatus.SYNTAX_ERROR, False),
    ],
)
def test_eligible_execution_statuses_produce_gold(status: HumanEvalStatus, expected: bool) -> None:
    result = verify_humaneval_execution(build_humaneval_execution_result(status))
    assert result.is_correct is expected


@pytest.mark.parametrize(
    "status",
    [
        HumanEvalStatus.TIMEOUT,
        HumanEvalStatus.CRASH,
        HumanEvalStatus.IMPORT_ERROR,
        HumanEvalStatus.VERIFIER_ERROR,
        HumanEvalStatus.SANDBOX_UNAVAILABLE,
        HumanEvalStatus.MALFORMED_OUTPUT,
        HumanEvalStatus.PROVIDER_FAILURE,
    ],
)
def test_infrastructure_and_provider_statuses_cannot_be_gold(status: HumanEvalStatus) -> None:
    with pytest.raises(ValueError, match="not eligible"):
        verify_humaneval_execution(build_humaneval_execution_result(status))
