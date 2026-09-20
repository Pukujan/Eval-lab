"""Compatibility module for the normalized Jev baseline runner."""

from eval_lab.jev import (
    ATOMIC_PROTOCOL,
    DIRECT_PROTOCOL,
    build_atomic_request,
    build_direct_request,
    normalize_atomic_response,
    normalize_direct_response,
    run_jev,
    run_jev_sync,
    write_predictions_jsonl,
)

__all__ = [
    "ATOMIC_PROTOCOL",
    "DIRECT_PROTOCOL",
    "build_atomic_request",
    "build_direct_request",
    "normalize_atomic_response",
    "normalize_direct_response",
    "run_jev",
    "run_jev_sync",
    "write_predictions_jsonl",
]
