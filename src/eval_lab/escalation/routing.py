"""Deterministic confidence routing and selective-risk summaries."""

from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from eval_lab.schema import ExecutionStatus, JudgePrediction, JudgeRecord


class Route(str, Enum):
    LOCAL = "local"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class RoutingRecord:
    """Minimal route decision before an optional provider outcome is attached."""

    record_id: str
    student_label: str | None
    student_raw_confidence: float | None
    student_calibrated_confidence: float | None
    confidence_margin: float | None
    threshold: float
    route: Route

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "student_label": self.student_label,
            "student_raw_confidence": self.student_raw_confidence,
            "student_calibrated_confidence": self.student_calibrated_confidence,
            "confidence_margin": self.confidence_margin,
            "threshold": self.threshold,
            "route": self.route.value,
        }


def _valid_confidence(value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or value < 0 or value > 1:
        raise ValueError("confidence must be finite and in [0, 1]")
    return value


def confidence_from_prediction(prediction: JudgePrediction, *, calibrated: bool = True) -> tuple[float, float]:
    """Return max probability and top-two margin with deterministic key ordering."""

    if prediction.execution_status is not ExecutionStatus.OK or not prediction.probabilities:
        raise ValueError("successful probability prediction required for routing")
    ordered = sorted((float(value) for value in prediction.probabilities.values()), reverse=True)
    confidence = _valid_confidence(ordered[0])
    margin = _valid_confidence(ordered[0] - (ordered[1] if len(ordered) > 1 else 0.0))
    return confidence, margin


def route_prediction(
    prediction: JudgePrediction,
    *,
    threshold: float,
    calibrated_confidence: float | None = None,
) -> RoutingRecord:
    """Route one local prediction; equality at the threshold is accepted."""

    threshold = _valid_confidence(threshold)
    raw_confidence, margin = confidence_from_prediction(prediction, calibrated=False)
    calibrated = raw_confidence if calibrated_confidence is None else _valid_confidence(calibrated_confidence)
    return RoutingRecord(
        record_id=prediction.record_id,
        student_label=prediction.label,
        student_raw_confidence=raw_confidence,
        student_calibrated_confidence=calibrated,
        confidence_margin=margin,
        threshold=threshold,
        route=Route.LOCAL if calibrated >= threshold else Route.ESCALATE,
    )


def wilson_interval(errors: int, count: int, *, confidence_level: float = 0.95) -> dict[str, float]:
    """Return a Wilson binomial interval, including an explicit empty-set interval."""

    if count < 0 or errors < 0 or errors > count:
        raise ValueError("errors must be between zero and count")
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between zero and one")
    if count == 0:
        return {"lower": 0.0, "upper": 1.0, "confidence_level": confidence_level}
    z = 1.959963984540054
    if confidence_level != 0.95:
        raise ValueError("only the preregistered 95% interval is supported")
    p = errors / count
    denominator = 1 + z * z / count
    center = (p + z * z / (2 * count)) / denominator
    radius = z * math.sqrt(p * (1 - p) / count + z * z / (4 * count * count)) / denominator
    return {
        "lower": max(0.0, center - radius),
        "upper": min(1.0, center + radius),
        "confidence_level": confidence_level,
    }


def _accepted_stats(
    records: Sequence[JudgeRecord],
    predictions: Sequence[JudgePrediction],
    threshold: float,
    *,
    calibrated_confidences: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    by_id = {record.record_id: record for record in records}
    if set(by_id) != {prediction.record_id for prediction in predictions}:
        raise ValueError("record and prediction IDs must match exactly")
    routes = [
        route_prediction(
            prediction,
            threshold=threshold,
            calibrated_confidence=(calibrated_confidences or {}).get(prediction.record_id),
        )
        for prediction in predictions
    ]
    accepted = [item for item in routes if item.route is Route.LOCAL]
    errors = sum(item.student_label != by_id[item.record_id].gold.label for item in accepted)
    interval = wilson_interval(errors, len(accepted))
    return {
        "threshold": threshold,
        "accepted_count": len(accepted),
        "error_count": errors,
        "risk": errors / len(accepted) if accepted else 0.0,
        "risk_interval_95": interval,
        "coverage": len(accepted) / len(routes) if routes else 0.0,
        "routes": routes,
    }


def select_threshold(
    records: Sequence[JudgeRecord],
    predictions: Sequence[JudgePrediction],
    *,
    target_error: float,
    calibrated_confidences: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Select maximum empirical local coverage at or below a target error."""

    target_error = _valid_confidence(target_error)
    by_id = {record.record_id: record for record in records}
    if set(by_id) != {prediction.record_id for prediction in predictions}:
        raise ValueError("record and prediction IDs must match exactly")
    points = []
    for prediction in predictions:
        confidence = _valid_confidence(
            (calibrated_confidences or {}).get(prediction.record_id, confidence_from_prediction(prediction)[0])
        )
        points.append((confidence, prediction.label != by_id[prediction.record_id].gold.label))
    candidates = sorted({0.0, 1.0, *(value for value, _ in points)}, reverse=True)
    by_confidence: dict[float, list[bool]] = {}
    for confidence, error in points:
        by_confidence.setdefault(confidence, []).append(error)
    error_count = 0
    accepted_count = 0
    summaries: list[dict[str, Any]] = []
    for threshold in candidates:
        for error in by_confidence.get(threshold, []):
            accepted_count += 1
            error_count += int(error)
        interval = wilson_interval(error_count, accepted_count)
        summaries.append(
            {
                "threshold": threshold,
                "accepted_count": accepted_count,
                "error_count": error_count,
                "risk": error_count / accepted_count if accepted_count else 0.0,
                "risk_interval_95": interval,
                "coverage": accepted_count / len(points) if points else 0.0,
            }
        )
    eligible = [item for item in summaries if item["risk"] <= target_error]
    selected = max(eligible, key=lambda item: (item["accepted_count"], item["threshold"])) if eligible else summaries[0]
    return {
        "target_error": target_error,
        "selected": {key: value for key, value in selected.items() if key != "routes"},
        "candidate_count": len(candidates),
        "confidence_supported": selected["risk_interval_95"]["upper"] <= target_error,
    }


def matched_random_record_ids(record_ids: Sequence[str], count: int, *, seed: int) -> list[str]:
    """Select exactly count unique IDs independent of input order."""

    unique = sorted(set(record_ids))
    if count < 0 or count > len(unique):
        raise ValueError("random sample count must be within unique record count")
    generator = random.Random(seed)
    return sorted(generator.sample(unique, count))


def evaluate_routing(
    records: Sequence[JudgeRecord],
    routed: Sequence[Mapping[str, Any]],
    *,
    domain_by_record_id: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Summarize resolved/unresolved route records without scoring failures as wrong."""

    by_id = {record.record_id: record for record in records}
    if set(by_id) != {str(row["record_id"]) for row in routed}:
        raise ValueError("routing records must cover the evaluation record IDs exactly")
    resolved = [row for row in routed if row.get("final_label") is not None]
    local = [row for row in routed if row.get("route") == Route.LOCAL.value]
    escalated = [row for row in routed if row.get("route") == Route.ESCALATE.value]
    local_errors = sum(row.get("final_label") != by_id[row["record_id"]].gold.label for row in local)
    final_errors = sum(row.get("final_label") != by_id[row["record_id"]].gold.label for row in resolved)
    domain_summary: dict[str, dict[str, int]] = {}
    for row in resolved:
        domain = (domain_by_record_id or {}).get(str(row["record_id"]), "unknown")
        domain_summary.setdefault(domain, {"count": 0, "errors": 0})
        domain_summary[domain]["count"] += 1
        domain_summary[domain]["errors"] += int(row.get("final_label") != by_id[row["record_id"]].gold.label)
    return {
        "total_count": len(routed),
        "execution_coverage": len(resolved) / len(routed) if routed else 0.0,
        "local_coverage": len(local) / len(routed) if routed else 0.0,
        "escalation_rate": len(escalated) / len(routed) if routed else 0.0,
        "unresolved_count": len(routed) - len(resolved),
        "unresolved_rate": (len(routed) - len(resolved)) / len(routed) if routed else 0.0,
        "local_accepted_count": len(local),
        "local_accepted_errors": local_errors,
        "local_accepted_risk": local_errors / len(local) if local else 0.0,
        "local_accepted_risk_interval_95": wilson_interval(local_errors, len(local)),
        "final_resolved_count": len(resolved),
        "final_resolved_errors": final_errors,
        "final_resolved_risk": final_errors / len(resolved) if resolved else None,
        "final_resolved_risk_interval_95": wilson_interval(final_errors, len(resolved)),
        "provider_status_counts": dict(Counter(str(row.get("provider_status", "not_called")) for row in routed)),
        "by_domain": domain_summary,
    }


__all__ = [
    "Route",
    "RoutingRecord",
    "confidence_from_prediction",
    "evaluate_routing",
    "matched_random_record_ids",
    "route_prediction",
    "select_threshold",
    "wilson_interval",
]
