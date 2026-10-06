from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from eval_lab.datasets.legalbench import (
    SUBTASK_NAMES,
    SUBTASK_SPECS,
    assign_case_splits,
    canonicalize_subtask_rows,
    case_split,
    majority_baseline,
)
from eval_lab.escalation.spec import build_decision_spec
from eval_lab.schema import GoldProvenance, JudgmentMode, Split

SEED = 261006
OVERRULING_PROMPT = "Sentence: {{text}}\nLabel:"
CITATION_PROMPT = "Sentence: {{text}}\nCitation: {{citation}}\nSupportive?"
EXPERIMENT_DIR = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "EXP-20261006-033-legalbench-answer-key-subset"
)


def overruling_row(index: int, text: str, answer: str) -> dict[str, str]:
    return {"index": str(index), "text": text, "answer": answer}


def citation_row(index: int, text: str, citation: str, answer: str) -> dict[str, str]:
    return {"index": str(index), "text": text, "citation": citation, "answer": answer}


def test_subtask_registry_names_and_columns() -> None:
    assert set(SUBTASK_NAMES) == {
        "overruling",
        "definition_classification",
        "citation_prediction_classification",
    }
    assert SUBTASK_SPECS["overruling"].columns == frozenset({"index", "text", "answer"})
    assert SUBTASK_SPECS["citation_prediction_classification"].columns == frozenset(
        {"index", "text", "citation", "answer"}
    )


def test_overruling_happy_path_emits_answer_key_records() -> None:
    rows = [overruling_row(0, "The court overruled the objection.", "Yes")]
    records = canonicalize_subtask_rows(
        rows, task="overruling", split=Split.TEST, prompt_template=OVERRULING_PROMPT
    )
    assert len(records) == 1
    record = records[0]
    assert record.mode is JudgmentMode.SINGLE
    assert record.gold.label == "Yes"
    assert record.gold.provenance is GoldProvenance.ANSWER_KEY
    assert record.gold.verifier_id == "legalbench-overruling-answer-key-v1"
    assert record.split is Split.TEST
    assert record.prompt == "Sentence: The court overruled the objection.\nLabel:"
    assert record.source_problem_id.startswith("legalbench-overruling:case:")


def test_citation_rows_sharing_text_share_problem_id_and_split() -> None:
    text = "SEC v. Sargent was decided on the pleadings."
    rows = [
        citation_row(48, text, "1 F.3d 1", "Yes"),
        citation_row(55, text, "2 F.3d 2", "No"),
    ]
    paired = assign_case_splits(rows, task="citation_prediction_classification", seed=SEED)
    assert paired[0][1] is paired[1][1]
    records = canonicalize_subtask_rows(
        rows,
        task="citation_prediction_classification",
        split=paired[0][1],
        prompt_template=CITATION_PROMPT,
    )
    assert {record.source_problem_id for record in records} == {records[0].source_problem_id}
    assert {record.gold.label for record in records} == {"Yes", "No"}
    assert "Citation: 1 F.3d 1" in records[0].prompt


def test_case_split_is_deterministic_and_normalization_insensitive() -> None:
    assert case_split("a  b", task="overruling", seed=SEED) is case_split(
        "a b", task="overruling", seed=SEED
    )
    assert case_split("same", task="overruling", seed=SEED) is case_split(
        "same", task="overruling", seed=SEED
    )


def test_normalization_collapses_only_whitespace() -> None:
    def problem_id(text: str) -> str:
        records = canonicalize_subtask_rows(
            [overruling_row(0, text, "Yes")],
            task="overruling",
            split=Split.TEST,
            prompt_template=OVERRULING_PROMPT,
        )
        return records[0].source_problem_id

    # Whitespace differences collapse to one case...
    assert problem_id("The  court\nruled") == problem_id("The court ruled")
    # ...but case and punctuation are preserved as distinct cases.
    assert problem_id("The court ruled") != problem_id("the court ruled")
    assert problem_id("The court ruled") != problem_id("The court ruled.")


def test_case_key_collapses_whitespace_only() -> None:
    # Same text modulo whitespace is one case; different text is a different case.
    assert case_split("a  b\nc", task="overruling", seed=SEED) is case_split(
        "a b c", task="overruling", seed=SEED
    )
    same = canonicalize_subtask_rows(
        [overruling_row(0, "The Court ruled.", "Yes")],
        task="overruling",
        split=Split.TEST,
        prompt_template=OVERRULING_PROMPT,
    )[0]
    different = canonicalize_subtask_rows(
        [overruling_row(0, "The court ruled!", "Yes")],
        task="overruling",
        split=Split.TEST,
        prompt_template=OVERRULING_PROMPT,
    )[0]
    assert same.source_problem_id != different.source_problem_id


def test_case_split_rejects_unknown_task() -> None:
    with pytest.raises(ValueError, match="unknown LegalBench subtask"):
        case_split("text", task="not_a_task", seed=SEED)


def test_missing_required_column_fails_closed() -> None:
    rows = [{"index": "0", "text": "t", "citation": "c"}]  # no answer
    with pytest.raises(ValueError, match="column mismatch"):
        canonicalize_subtask_rows(
            rows,
            task="citation_prediction_classification",
            split=Split.TEST,
            prompt_template=CITATION_PROMPT,
        )


def test_missing_citation_column_fails_closed() -> None:
    rows = [{"index": "0", "text": "t", "answer": "Yes"}]
    with pytest.raises(ValueError, match="column mismatch"):
        canonicalize_subtask_rows(
            rows,
            task="citation_prediction_classification",
            split=Split.TEST,
            prompt_template=CITATION_PROMPT,
        )


def test_extra_column_fails_closed() -> None:
    rows = [{"index": "0", "text": "t", "answer": "Yes", "slice": "x"}]
    with pytest.raises(ValueError, match="column mismatch"):
        canonicalize_subtask_rows(
            rows, task="overruling", split=Split.TEST, prompt_template=OVERRULING_PROMPT
        )


def test_citation_column_passed_to_overruling_fails_closed() -> None:
    rows = [citation_row(0, "t", "c", "Yes")]
    with pytest.raises(ValueError, match="column mismatch"):
        canonicalize_subtask_rows(
            rows, task="overruling", split=Split.TEST, prompt_template=OVERRULING_PROMPT
        )


def test_unsupported_label_fails_closed() -> None:
    rows = [overruling_row(0, "t", "Maybe")]
    with pytest.raises(ValueError, match="unsupported overruling answer label"):
        canonicalize_subtask_rows(
            rows, task="overruling", split=Split.TEST, prompt_template=OVERRULING_PROMPT
        )


def test_empty_text_fails_closed() -> None:
    rows = [overruling_row(0, "   ", "Yes")]
    with pytest.raises(ValueError, match="text must be non-empty"):
        canonicalize_subtask_rows(
            rows, task="overruling", split=Split.TEST, prompt_template=OVERRULING_PROMPT
        )


def test_duplicate_index_fails_closed() -> None:
    rows = [overruling_row(0, "a", "Yes"), overruling_row(0, "b", "No")]
    with pytest.raises(ValueError, match="duplicate overruling row index"):
        canonicalize_subtask_rows(
            rows, task="overruling", split=Split.TEST, prompt_template=OVERRULING_PROMPT
        )


def test_non_integer_index_fails_closed() -> None:
    rows = [overruling_row(0, "a", "Yes")]
    rows[0]["index"] = "x"
    with pytest.raises(ValueError, match="index must be an integer"):
        canonicalize_subtask_rows(
            rows, task="overruling", split=Split.TEST, prompt_template=OVERRULING_PROMPT
        )


def test_wrong_slot_count_fails_closed() -> None:
    rows = [overruling_row(0, "a", "Yes")]
    with pytest.raises(ValueError, match="exactly one .* slot"):
        canonicalize_subtask_rows(
            rows, task="overruling", split=Split.TEST, prompt_template="Sentence: {{text}}{{text}}"
        )
    with pytest.raises(ValueError, match="exactly one .* slot"):
        canonicalize_subtask_rows(
            rows,
            task="citation_prediction_classification",
            split=Split.TEST,
            prompt_template="Sentence: {{text}}",  # missing {{citation}}
        )


def test_assign_case_splits_are_disjoint_across_cases() -> None:
    rows = [
        overruling_row(0, "alpha", "Yes"),
        overruling_row(1, "beta", "No"),
        overruling_row(2, "gamma", "Yes"),
    ]
    paired = assign_case_splits(rows, task="overruling", seed=SEED)
    by_split: dict[Split, set[str]] = {Split.CALIBRATION: set(), Split.TEST: set()}
    for row, split in paired:
        records = canonicalize_subtask_rows(
            [row], task="overruling", split=split, prompt_template=OVERRULING_PROMPT
        )
        by_split[split].add(records[0].source_problem_id)
    assert not (by_split[Split.CALIBRATION] & by_split[Split.TEST])


def test_labels_are_covered_and_provenance_is_answer_key() -> None:
    rows = [
        overruling_row(0, "a", "Yes"),
        overruling_row(1, "b", "No"),
    ]
    records = canonicalize_subtask_rows(
        rows, task="overruling", split=Split.TEST, prompt_template=OVERRULING_PROMPT
    )
    labels = {record.gold.label for record in records}
    assert labels == {"Yes", "No"}
    assert all(record.gold.provenance is GoldProvenance.ANSWER_KEY for record in records)


def test_majority_baseline_reports_a_tie() -> None:
    baseline = majority_baseline(["Yes", "Yes", "No", "No"])
    assert baseline["tie"] is True
    assert baseline["accuracy"] == 0.5
    assert baseline["counts"] == {"No": 2, "Yes": 2}


def test_majority_baseline_reports_a_winner() -> None:
    baseline = majority_baseline(["Yes", "Yes", "Yes", "No"])
    assert baseline["tie"] is False
    assert baseline["label"] == "Yes"
    assert baseline["accuracy"] == 0.75


def test_typed_spec_carries_native_yes_no_label_space() -> None:
    # The documented scoring path: a supplied label_set replaces the default
    # pass/fail space, so a "Yes" gold is inside the closed label space.
    record = canonicalize_subtask_rows(
        [overruling_row(0, "The court overruled the objection.", "Yes")],
        task="overruling",
        split=Split.TEST,
        prompt_template=OVERRULING_PROMPT,
    )[0]
    spec = build_decision_spec(record, label_set=["Yes", "No"])
    assert spec.legal_labels == ["Yes", "No"]
    assert record.gold.label in spec.legal_labels
    payload = spec.provider_payload()
    question = payload["questions"]["verdict"]
    assert set(question["criteria"]) == {"Yes", "No"}


def test_default_single_mode_path_cannot_hold_native_yes_no_gold() -> None:
    # Without label_set the single-mode space stays pass/fail, so native Yes/No
    # gold falls outside it. This is why EXP-033 must score through the typed
    # path and must not use the default single-mode path.
    record = canonicalize_subtask_rows(
        [overruling_row(0, "The court overruled the objection.", "Yes")],
        task="overruling",
        split=Split.TEST,
        prompt_template=OVERRULING_PROMPT,
    )[0]
    spec = build_decision_spec(record)
    assert spec.legal_labels == ["pass", "fail"]
    assert record.gold.label not in spec.legal_labels


def test_frozen_canonical_matches_preregistered_fingerprint() -> None:
    # The dataset fingerprint is the raw-byte SHA-256 of canonical-records.jsonl
    # and is line-ending sensitive, so the committed artifact must be LF-only
    # (see the EXP-033 .gitattributes rule) and match experiment.yaml.
    canonical = EXPERIMENT_DIR / "canonical-records.jsonl"
    raw = canonical.read_bytes()
    assert b"\r\n" not in raw
    digest = hashlib.sha256(raw).hexdigest()
    manifest = json.loads((EXPERIMENT_DIR / "source-manifest.json").read_text(encoding="utf-8"))
    assert manifest["canonical_records_sha256"] == digest
    preregistered = (EXPERIMENT_DIR / "experiment.yaml").read_text(encoding="utf-8")
    assert re.search(rf"fingerprint: sha256:{digest}\b", preregistered)
