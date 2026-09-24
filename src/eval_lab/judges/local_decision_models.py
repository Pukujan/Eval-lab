"""Jev-style request and prediction normalization for local decision models."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

PROTOCOL_VERSION = "eval-lab-local-decision-v1"
ABSTENTION_LABELS = {"__insufficient_evidence__", "insufficient_evidence", "abstain"}


def request_for_record(record: Mapping[str, Any], benchmark: str) -> dict[str, Any]:
    """Build one fixed-choice request without including the gold label."""

    prompt = str(record["prompt"])
    rubric = record.get("rubric", [])
    instructions = " ".join(str(item["description"]) for item in rubric).strip()
    if benchmark == "exp028-legalbench-hearsay":
        labels = ["Yes", "No"]
        options = {
            "Yes": "The evidence qualifies as hearsay under the definition and task prompt.",
            "No": "The evidence does not qualify as hearsay under the definition and task prompt.",
        }
        state: str | dict[str, Any] = prompt
        question = instructions or "Is the described evidence hearsay?"
    elif benchmark == "exp027-frozen-pool":
        mode = str(record["mode"])
        if mode == "single":
            labels = ["pass", "fail"]
            options = {
                "pass": "Candidate A satisfies the stated criterion.",
                "fail": "Candidate A does not satisfy the stated criterion.",
            }
            question = instructions or "Does candidate A satisfy the criterion?"
        elif mode == "pairwise":
            labels = ["A", "B", "TIE"]
            options = {
                "A": "Candidate A is better according to the stated criterion.",
                "B": "Candidate B is better according to the stated criterion.",
                "TIE": "The candidates are equally good under the stated criterion.",
            }
            question = instructions or "Which candidate better satisfies the criterion?"
        else:
            raise ValueError(f"unsupported judgment mode: {mode!r}")
        state = {
            "prompt": prompt,
            "candidate_a": str(record["candidate_a"]),
            "candidate_b": record.get("candidate_b"),
            "mode": mode,
        }
    else:
        raise ValueError(f"unsupported benchmark: {benchmark!r}")

    return {
        "record_id": str(record["record_id"]),
        "state": state,
        "question": question,
        "options": [{"id": label, "description": options[label]} for label in labels],
        "labels": labels,
    }


def normalize_probabilities(
    raw: Mapping[str, Any] | Sequence[Any], labels: Sequence[str]
) -> tuple[dict[str, float] | None, dict[str, float] | None, str | None]:
    """Return raw and normalized legal-option probabilities, or a validation error."""

    if isinstance(raw, Mapping):
        raw_map = {str(key): _finite_probability(value) for key, value in raw.items()}
    elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        if len(raw) != len(labels):
            return None, None, "probability_count_mismatch"
        raw_map = {
            label: _finite_probability(value) for label, value in zip(labels, raw, strict=True)
        }
    else:
        return None, None, "probabilities_missing_or_not_a_map"

    if any(value is None for value in raw_map.values()):
        return None, None, "invalid_probability_value"
    raw_values = {key: float(value) for key, value in raw_map.items() if value is not None}
    if not raw_values or sum(raw_values.values()) <= 0:
        return None, None, "empty_or_zero_probability_mass"
    if any(value < 0 or value > 1 for value in raw_values.values()):
        return None, None, "probability_out_of_range"
    if not math.isclose(sum(raw_values.values()), 1.0, abs_tol=1e-3):
        return None, raw_values, "probability_mass_does_not_sum_to_one"

    legal = {label: raw_values.get(label, 0.0) for label in labels}
    legal_mass = sum(legal.values())
    if legal_mass <= 0:
        return None, raw_values, "no_probability_mass_for_legal_labels"
    normalized = {label: value / legal_mass for label, value in legal.items()}
    return normalized, raw_values, None


def normalize_choice_output(
    *,
    selected: Any,
    probabilities: Mapping[str, Any] | Sequence[Any] | None,
    labels: Sequence[str],
    raw_scores: Mapping[str, Any] | Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Normalize a backend choice while retaining its complete native distribution."""

    selected_label = str(selected) if selected is not None else ""
    if not selected_label:
        return {"ok": False, "error": "selected_label_missing"}
    if selected_label in ABSTENTION_LABELS:
        normalized, raw, error = normalize_probabilities(probabilities or {}, labels)
        return {
            "ok": False,
            "abstained": True,
            "error": error,
            "raw_probabilities": raw,
            "raw_scores": _score_map(raw_scores, labels),
        }
    if selected_label not in labels:
        return {"ok": False, "error": "selected_label_outside_declared_choices"}
    normalized, raw, error = normalize_probabilities(probabilities or {}, labels)
    if error:
        return {"ok": False, "error": error, "raw_probabilities": raw}
    assert normalized is not None
    if selected_label != max(normalized, key=normalized.__getitem__):
        return {
            "ok": False,
            "error": "selected_label_disagrees_with_probability_argmax",
            "raw_probabilities": raw,
        }
    return {
        "ok": True,
        "label": selected_label,
        "probabilities": normalized,
        "raw_probabilities": raw,
        "raw_scores": _score_map(raw_scores, labels),
        "probability_semantics": "conditional on a non-abstain option"
        if raw and len(raw) > len(labels)
        else "native over declared options",
    }


def _finite_probability(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _score_map(
    raw: Mapping[str, Any] | Sequence[Any] | None, labels: Sequence[str]
) -> dict[str, float] | None:
    if isinstance(raw, Mapping):
        result: dict[str, float] = {}
        for key, value in raw.items():
            number = _finite_probability(value)
            if number is None:
                return None
            result[str(key)] = number
        return result or None
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)) and len(raw) == len(labels):
        result = {}
        for label, value in zip(labels, raw, strict=True):
            number = _finite_probability(value)
            if number is None:
                return None
            result[label] = number
        return result
    return None


__all__ = [
    "PROTOCOL_VERSION",
    "normalize_choice_output",
    "normalize_probabilities",
    "request_for_record",
]
