from __future__ import annotations

import json

from eval_lab.judges.local_decision_models import normalize_choice_output, request_for_record


def test_exp027_single_request_uses_fixed_labels_and_hides_gold() -> None:
    record = {
        "record_id": "single-1",
        "mode": "single",
        "prompt": "Which option is correct?",
        "candidate_a": "B) blue",
        "candidate_b": None,
        "rubric": [{"description": "The candidate selects the answer-key choice."}],
        "gold": {"label": "pass"},
    }

    request = request_for_record(record, "exp027-frozen-pool")

    assert request["labels"] == ["pass", "fail"]
    assert json.loads(request["state"])["candidate_a"] == "B) blue"
    assert "gold" not in str(request)


def test_exp027_pairwise_and_legalbench_labels_are_stable() -> None:
    pair = {
        "record_id": "pair-1",
        "mode": "pairwise",
        "prompt": "Compare the candidates.",
        "candidate_a": "first",
        "candidate_b": "second",
        "rubric": [],
    }
    legal = {
        "record_id": "hearsay-1",
        "prompt": "Is this hearsay?",
        "rubric": [],
    }

    assert request_for_record(pair, "exp027-frozen-pool")["labels"] == ["A", "B", "TIE"]
    assert request_for_record(legal, "exp028-legalbench-hearsay")["labels"] == ["Yes", "No"]


def test_choice_output_preserves_abstention_mass_and_conditions_legal_probs() -> None:
    result = normalize_choice_output(
        selected="Yes",
        probabilities={"Yes": 0.6, "No": 0.2, "__insufficient_evidence__": 0.2},
        labels=["Yes", "No"],
    )

    assert result["ok"] is True
    assert result["label"] == "Yes"
    assert round(result["probabilities"]["Yes"], 12) == 0.75
    assert round(result["probabilities"]["No"], 12) == 0.25
    assert result["raw_probabilities"]["__insufficient_evidence__"] == 0.2


def test_choice_output_rejects_inconsistent_or_malformed_probabilities() -> None:
    inconsistent = normalize_choice_output(
        selected="No", probabilities={"Yes": 0.7, "No": 0.3}, labels=["Yes", "No"]
    )
    malformed = normalize_choice_output(
        selected="Yes", probabilities={"Yes": 0.7, "No": 0.2}, labels=["Yes", "No"]
    )

    assert inconsistent["error"] == "selected_label_disagrees_with_probability_argmax"
    assert malformed["error"] == "probability_mass_does_not_sum_to_one"
