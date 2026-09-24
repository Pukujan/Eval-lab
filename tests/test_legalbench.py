from __future__ import annotations

import pytest

from eval_lab.datasets.legalbench import canonicalize_hearsay_rows
from eval_lab.schema import GoldProvenance, Split


@pytest.fixture
def hearsay_prompt() -> str:
    return "Example: {{text}}\nAnswer:"


def row(index: int = 7, answer: str = "Yes") -> dict[str, str]:
    return {
        "index": str(index),
        "answer": answer,
        "text": "A witness repeats an out-of-court assertion.",
        "slice": "Standard hearsay",
    }


def test_canonicalizes_hearsay_answer_key_and_source_identity(hearsay_prompt: str) -> None:
    record = canonicalize_hearsay_rows([row()], split=Split.TEST, prompt_template=hearsay_prompt)[0]

    assert record.record_id == "legalbench-hearsay:test:7"
    assert record.source_problem_id == record.record_id
    assert record.split is Split.TEST
    assert record.prompt == "Example: A witness repeats an out-of-court assertion.\nAnswer:"
    assert record.gold.label == "Yes"
    assert record.gold.provenance is GoldProvenance.ANSWER_KEY
    assert record.gold.evidence == {
        "task": "hearsay",
        "slice": "Standard hearsay",
        "source_index": 7,
    }


def test_split_is_part_of_source_id_for_split_local_indices(hearsay_prompt: str) -> None:
    train = canonicalize_hearsay_rows([row(0)], split=Split.TRAIN, prompt_template=hearsay_prompt)[
        0
    ]
    test = canonicalize_hearsay_rows([row(0)], split=Split.TEST, prompt_template=hearsay_prompt)[0]

    assert train.source_problem_id != test.source_problem_id


@pytest.mark.parametrize(
    "bad_row",
    [
        {"index": "x", "answer": "Yes", "text": "Evidence", "slice": "Standard hearsay"},
        row(answer="Maybe"),
        {"index": "1", "answer": "No", "text": "", "slice": "Standard hearsay"},
    ],
)
def test_rejects_invalid_hearsay_rows(bad_row: dict[str, str], hearsay_prompt: str) -> None:
    with pytest.raises(ValueError):
        canonicalize_hearsay_rows([bad_row], split=Split.TEST, prompt_template=hearsay_prompt)


def test_rejects_duplicate_source_indices(hearsay_prompt: str) -> None:
    with pytest.raises(ValueError, match="duplicate Hearsay row index"):
        canonicalize_hearsay_rows(
            [row(2), row(2)], split=Split.TEST, prompt_template=hearsay_prompt
        )


def test_requires_one_prompt_slot() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        canonicalize_hearsay_rows([row()], split=Split.TEST, prompt_template="No slot")
