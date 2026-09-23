"""Per-policy selective-escalation metrics using existing metric primitives."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from eval_lab.escalation.routing import Route, evaluate_routing, wilson_interval
from eval_lab.metrics.classification import classification_metrics
from eval_lab.metrics.latency import latency_summary
from eval_lab.metrics.risk import risk_coverage_curve
from eval_lab.schema import JudgePrediction, JudgeRecord

TARGET_ERRORS = (0.01, 0.02, 0.05, 0.10)

REQUIRED_POLICY_METRIC_KEYS = (
    "accuracy",
    "balanced_accuracy",
    "macro_f1",
    "execution_coverage",
    "local_coverage",
    "escalation_rate",
    "local_accepted_risk",
    "local_accepted_risk_interval_95",
    "final_resolved_risk",
    "final_resolved_risk_interval_95",
    "unresolved_rate",
    "probability_metrics",
    "latency",
    "external_calls",
    "external_calls_per_1000",
    "provider_resources",
    "aggregate",
    "by_domain",
    "risk_coverage",
    "selected_operating_point",
)


def _claim_status(supported: bool) -> str:
    return "confidence-supported" if supported else "descriptive"


def _class_order(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    probabilities: Sequence[Mapping[str, float] | None] | None,
) -> list[str]:
    classes = list(dict.fromkeys([*y_true, *y_pred]))
    if probabilities:
        for row in probabilities:
            if row is None:
                continue
            for label in row:
                if label not in classes:
                    classes.append(label)
    return classes


def _classification_or_empty(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    probabilities: Sequence[Mapping[str, float] | None] | None,
) -> dict[str, float | None]:
    if not y_true:
        return {
            "accuracy": None,
            "balanced_accuracy": None,
            "macro_f1": None,
            "brier": None,
            "nll": None,
            "ece": None,
        }
    return classification_metrics(
        y_true,
        y_pred,
        probabilities,
        class_order=_class_order(y_true, y_pred, probabilities),
    )


def _probability_bundle(
    metrics: Mapping[str, float | None], *, available: bool, reason: str | None
) -> dict[str, Any]:
    return {
        "available": available,
        "brier": metrics.get("brier"),
        "nll": metrics.get("nll"),
        "ece": metrics.get("ece"),
        "unavailable_reason": None if available else reason,
    }


def _target_coverage(
    correct: Sequence[bool],
    confidence: Sequence[float],
    target_errors: Sequence[float],
) -> dict[str, Any]:
    ranked = sorted(enumerate(confidence), key=lambda item: (-item[1], item[0]))
    output: dict[str, Any] = {}
    for target in target_errors:
        errors = 0
        best: dict[str, float | int] = {
            "coverage": 0.0,
            "risk": 0.0,
            "accepted_count": 0,
            "error_count": 0,
            "threshold": 1.0,
        }
        for accepted, (index, score) in enumerate(ranked, start=1):
            errors += int(not correct[index])
            risk = errors / accepted
            if risk <= target:
                best = {
                    "coverage": accepted / len(ranked),
                    "risk": risk,
                    "accepted_count": accepted,
                    "error_count": errors,
                    "threshold": float(score),
                }
        interval = wilson_interval(int(best["error_count"]), int(best["accepted_count"]))
        supported = bool(best["accepted_count"] and interval["upper"] <= target)
        output[f"{target:.2f}"] = {
            **best,
            "risk_interval_95": interval,
            "confidence_supported": supported,
            "claim_status": _claim_status(supported),
        }
    return output


def _provider_resources(predictions: Sequence[JudgePrediction]) -> dict[str, Any]:
    models = [prediction.judge_id for prediction in predictions]
    model = models[0] if len(set(models)) == 1 else None
    input_tokens = 0.0
    output_tokens = 0.0
    cost = 0.0
    usage_calls = 0
    for prediction in predictions:
        usage = prediction.provider_metadata.get("usage")
        if not isinstance(usage, dict):
            continue
        usage_calls += 1
        input_tokens += float(usage.get("input_tokens", 0.0) or 0.0)
        output_tokens += float(usage.get("output_tokens", 0.0) or 0.0)
        cost += float(usage.get("cost", 0.0) or 0.0)
    if not predictions:
        return {
            "model": None,
            "calls": 0,
            "cost": 0.0,
            "input_tokens": 0.0,
            "output_tokens": 0.0,
            "usage_available_calls": 0,
            "available": True,
            "unavailable_reason": None,
        }
    available = usage_calls > 0
    return {
        "model": model,
        "calls": len(predictions),
        "cost": cost if available else None,
        "input_tokens": input_tokens if available else None,
        "output_tokens": output_tokens if available else None,
        "usage_available_calls": usage_calls,
        "available": available,
        "unavailable_reason": None if available else "provider did not report usage",
    }


def summarize_policy_metrics(
    records: Sequence[JudgeRecord],
    routed: Sequence[Mapping[str, Any]],
    *,
    domain_by_record_id: Mapping[str, str] | None = None,
    selected_predictions: Mapping[str, JudgePrediction] | None = None,
    ranking_correct: Sequence[bool] | None = None,
    ranking_confidence: Sequence[float] | None = None,
    target_error: float | None = None,
    target_errors: Sequence[float] = TARGET_ERRORS,
    threshold: float | None = None,
) -> dict[str, Any]:
    """Assemble TASK-0010 policy metrics without selecting thresholds from final labels."""

    routing = evaluate_routing(records, routed, domain_by_record_id=domain_by_record_id)
    by_id = {record.record_id: record for record in records}
    predictions = selected_predictions or {}
    resolved_true: list[str] = []
    resolved_pred: list[str] = []
    resolved_prob: list[Mapping[str, float] | None] = []
    latencies: list[float] = []
    provider_preds: list[JudgePrediction] = []
    domain_pairs: dict[str, list[tuple[str, str, Mapping[str, float] | None]]] = {}
    for row in routed:
        record = by_id[str(row["record_id"])]
        prediction = predictions.get(record.record_id)
        if prediction is not None and prediction.latency_ms is not None:
            latencies.append(float(prediction.latency_ms))
        if (
            row.get("route") == Route.ESCALATE.value
            and prediction is not None
            and str(row.get("provider_status", "not_called")) != "not_called"
        ):
            provider_preds.append(prediction)
        if row.get("final_label") is None:
            continue
        label = str(row["final_label"])
        resolved_true.append(record.gold.label)
        resolved_pred.append(label)
        probability = prediction.probabilities if prediction is not None else None
        resolved_prob.append(probability)
        domain = (domain_by_record_id or {}).get(record.record_id, "unknown")
        domain_pairs.setdefault(domain, []).append((record.gold.label, label, probability))

    probability_available = bool(resolved_true) and all(row is not None for row in resolved_prob)
    metrics = _classification_or_empty(
        resolved_true,
        resolved_pred,
        resolved_prob if probability_available else None,
    )
    probability_reason = None
    if not resolved_true:
        probability_reason = "no resolved predictions"
    elif not probability_available:
        probability_reason = "one or more resolved predictions did not provide probabilities"
    latency: dict[str, Any] = dict(latency_summary(latencies))
    latency["available"] = bool(latencies)
    latency["unavailable_reason"] = None if latencies else "no latency observations for this policy"
    external_calls = sum(
        1
        for row in routed
        if row.get("route") == Route.ESCALATE.value
        and str(row.get("provider_status", "not_called")) != "not_called"
    )
    by_domain: dict[str, Any] = {}
    for domain, rows in routing["by_domain"].items():
        pairs = domain_pairs.get(domain, [])
        domain_available = bool(pairs) and all(item[2] is not None for item in pairs)
        domain_metrics = _classification_or_empty(
            [item[0] for item in pairs],
            [item[1] for item in pairs],
            [item[2] for item in pairs] if domain_available else None,
        )
        by_domain[domain] = {
            **rows,
            "metrics": domain_metrics,
            "probability_metrics_available": domain_available,
        }
    ranking_available = (
        ranking_correct is not None
        and ranking_confidence is not None
        and len(ranking_correct) == len(ranking_confidence) > 0
    )
    risk_coverage: dict[str, Any]
    if ranking_available:
        assert ranking_correct is not None
        assert ranking_confidence is not None
        curve = [
            point.as_dict() for point in risk_coverage_curve(ranking_correct, ranking_confidence)
        ]
        coverage_flags = _target_coverage(ranking_correct, ranking_confidence, target_errors)
        risk_coverage = {
            "available": True,
            "unavailable_reason": None,
            "curve": curve,
            "coverage_at_target_error": coverage_flags,
        }
    else:
        risk_coverage = {
            "available": False,
            "unavailable_reason": "student ranking confidence was not supplied for this policy",
            "curve": [],
            "coverage_at_target_error": {
                f"{target:.2f}": {
                    "coverage": None,
                    "risk": None,
                    "accepted_count": 0,
                    "error_count": 0,
                    "threshold": None,
                    "risk_interval_95": wilson_interval(0, 0),
                    "confidence_supported": False,
                    "claim_status": "descriptive",
                }
                for target in target_errors
            },
        }
    operating = None
    if target_error is not None:
        interval = routing["local_accepted_risk_interval_95"]
        supported = bool(routing["local_accepted_count"] and interval["upper"] <= target_error)
        operating = {
            "target_error": target_error,
            "threshold": threshold,
            "local_coverage": routing["local_coverage"],
            "local_accepted_risk": routing["local_accepted_risk"],
            "risk_interval_95": interval,
            "confidence_supported": supported,
            "claim_status": _claim_status(supported),
            "collapsed": False,
        }
    return {
        **routing,
        "accuracy": metrics["accuracy"],
        "balanced_accuracy": metrics["balanced_accuracy"],
        "macro_f1": metrics["macro_f1"],
        "probability_metrics": _probability_bundle(
            metrics,
            available=probability_available,
            reason=probability_reason,
        ),
        "latency": latency,
        "external_calls": external_calls,
        "external_calls_per_1000": (1000.0 * external_calls / len(routed)) if routed else 0.0,
        "provider_resources": _provider_resources(provider_preds),
        "aggregate": {
            "count": len(resolved_true),
            "metrics": metrics,
            "probability_metrics_available": probability_available,
        },
        "by_domain": by_domain,
        "risk_coverage": risk_coverage,
        "selected_operating_point": operating,
        "provider_status_counts": dict(
            Counter(str(row.get("provider_status", "not_called")) for row in routed)
        ),
    }


__all__ = [
    "REQUIRED_POLICY_METRIC_KEYS",
    "TARGET_ERRORS",
    "summarize_policy_metrics",
]
