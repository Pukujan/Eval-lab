"""Latency summaries with deterministic percentile interpolation."""

from __future__ import annotations

from collections.abc import Sequence


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def latency_summary(latencies_ms: Sequence[float]) -> dict[str, float | int | None]:
    if not latencies_ms:
        return {"count": 0, "mean_ms": None, "median_ms": None, "p95_ms": None, "min_ms": None, "max_ms": None}
    if any(value < 0 for value in latencies_ms):
        raise ValueError("latencies must be non-negative")
    values = [float(value) for value in latencies_ms]
    return {
        "count": len(values),
        "mean_ms": sum(values) / len(values),
        "median_ms": _percentile(values, 0.5),
        "p95_ms": _percentile(values, 0.95),
        "min_ms": min(values),
        "max_ms": max(values),
    }
