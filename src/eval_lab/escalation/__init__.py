"""Provider-independent selective escalation primitives."""

from eval_lab.escalation.providers import (
    OPENROUTER_DECISIONS_URL,
    OPENROUTER_PINNED_MODEL,
    OPENROUTER_ROLLING_MODEL,
    SYSTEM_ONE_PROTOCOL,
    YOLO_AUTO_BASE_URL,
    YOLO_QWEN_MODEL,
    normalize_typed_response,
    run_openrouter_jev,
    run_yolo_qwen,
)
from eval_lab.escalation.routing import (
    Route,
    RoutingRecord,
    confidence_from_prediction,
    evaluate_routing,
    matched_random_record_ids,
    route_prediction,
    select_threshold,
    wilson_interval,
)
from eval_lab.escalation.spec import DecisionSpec, TypedQuestion, build_decision_spec

__all__ = [
    "OPENROUTER_DECISIONS_URL",
    "OPENROUTER_PINNED_MODEL",
    "OPENROUTER_ROLLING_MODEL",
    "SYSTEM_ONE_PROTOCOL",
    "YOLO_AUTO_BASE_URL",
    "YOLO_QWEN_MODEL",
    "DecisionSpec",
    "Route",
    "RoutingRecord",
    "TypedQuestion",
    "build_decision_spec",
    "confidence_from_prediction",
    "evaluate_routing",
    "matched_random_record_ids",
    "normalize_typed_response",
    "route_prediction",
    "run_openrouter_jev",
    "run_yolo_qwen",
    "select_threshold",
    "wilson_interval",
]
