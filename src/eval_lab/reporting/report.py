"""Aggregate and per-domain report generation."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from eval_lab.metrics.summary import evaluate_prediction_set
from eval_lab.schema import JudgePrediction, JudgeRecord


def build_report(
    records: Sequence[JudgeRecord],
    predictions: Sequence[JudgePrediction],
    *,
    domain_by_record_id: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Build a JSON-serializable report while preserving provider failures."""

    report = evaluate_prediction_set(records, predictions, domain_by_record_id=domain_by_record_id)
    report["probability_metrics"] = {
        "available": bool(report["aggregate"]["probability_metrics_available"]),
        "unavailable_reason": None
        if report["aggregate"]["probability_metrics_available"]
        else "one or more successful predictions did not provide probabilities",
    }
    return report


generate_report = build_report


def render_report_markdown(report: dict[str, object]) -> str:
    """Render the stable top-level report fields as concise Markdown."""

    aggregate = report.get("aggregate") or {}
    metrics = aggregate.get("metrics") if isinstance(aggregate, dict) else None
    lines = [
        "# Eval Lab Report",
        "",
        f"- Total predictions: {report.get('total_count', 0)}",
        f"- Successful predictions: {report.get('successful_count', 0)}",
        f"- Failure count: {report.get('failure_count', 0)}",
    ]
    if isinstance(metrics, dict):
        lines.extend(["", "## Aggregate metrics", "", "| Metric | Value |", "| --- | ---: |"])
        lines.extend(f"| {name} | {value} |" for name, value in metrics.items())
    probability = report.get("probability_metrics", {})
    if isinstance(probability, dict) and not probability.get("available", False):
        lines.extend(["", f"Probability metrics unavailable: {probability.get('unavailable_reason')}."])
    return "\n".join(lines) + "\n"


def write_report(report: dict[str, object], path: str | Path) -> Path:
    """Write JSON and Markdown report formats based on the destination suffix."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.suffix.lower() in {".md", ".markdown"}:
        destination.write_text(render_report_markdown(report), encoding="utf-8")
    else:
        destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination


__all__ = ["build_report", "generate_report", "render_report_markdown", "write_report"]
