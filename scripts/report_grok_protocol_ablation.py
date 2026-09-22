"""Generate the offline report and preregistered protocol-selection decision."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BASELINE = "typed_schema"


def _load_runs(root: Path) -> list[dict[str, Any]]:
    runs = []
    for result_path in sorted(root.glob("*/results.json")):
        runs.append(json.loads(result_path.read_text(encoding="utf-8")))
    if not runs:
        raise ValueError(f"no run results under {root}")
    return runs


def choose_variant(runs: list[dict[str, Any]], *, model: str = "grok_46") -> dict[str, Any]:
    public = [run for run in runs if run["partition"] == "public_selection" and run["arm_id"] == model]
    by_variant = {run["variant"]: run for run in public}
    if BASELINE not in by_variant:
        raise ValueError(f"public {model} baseline is missing")
    baseline = by_variant[BASELINE]["summary"]
    baseline_score = baseline["selection_score"]
    eligible: list[dict[str, Any]] = []
    for run in by_variant.values():
        summary = run["summary"]
        if (
            summary["resolved_count"] >= 64
            and summary["coverage"] >= 0.95
            and baseline_score is not None
            and summary["selection_score"] is not None
            and summary["selection_score"] >= baseline_score + 0.10
        ):
            eligible.append(run)
    if eligible:
        selected = max(
            eligible,
            key=lambda run: (run["summary"]["selection_score"], run["summary"]["coverage"], run["variant"]),
        )
        reason = "passed public gate and maximized mode-balanced accuracy"
        gate = True
    else:
        selected = by_variant[BASELINE]
        reason = "no alternative passed the preregistered public gate; rerun baseline"
        gate = False
    return {
        "model": model,
        "baseline_variant": BASELINE,
        "baseline_score": baseline_score,
        "selected_variant": selected["variant"],
        "selected_score": selected["summary"]["selection_score"],
        "gate_passed": gate,
        "reason": reason,
    }


def _row(run: dict[str, Any]) -> str:
    summary = run["summary"]
    statuses = ", ".join(f"{key}={value}" for key, value in sorted(summary["status_counts"].items()))
    return (
        f"| `{run['arm_id']}` | `{run['variant']}` | {summary['resolved_count']}/{summary['record_count']} | "
        f"{summary['coverage']:.4f} | {summary['selection_score'] if summary['selection_score'] is not None else 'n/a'} | `{statuses}` |"
    )


def write_report(*, root: Path, output: Path) -> dict[str, Any]:
    runs = _load_runs(root)
    selection = choose_variant(runs)
    output.mkdir(parents=True, exist_ok=True)
    (output / "selection.json").write_text(json.dumps(selection, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# EXP-20260922-025 — Grok protocol ablation",
        "",
        "Provider statuses remain unresolved and are not counted as labels.",
        "",
        "## Public protocol selection",
        "",
        f"Primary model: `grok_46`; baseline: `{BASELINE}`; selected variant: `{selection['selected_variant']}`.",
        f"Gate passed: `{selection['gate_passed']}` — {selection['reason']}.",
        "The first no-schema pass exposed a Windows locale-decoding failure in the shared stream reader; it was stopped and resumed from its normalized checkpoint after the UTF-8-safe reader repair. Only the repaired arm's final results are used below.",
        "",
        "| Arm | Variant | Resolved | Coverage | Mode-balanced score | Statuses |",
        "|---|---|---:|---:|---:|---|",
    ]
    for run in runs:
        if run["partition"] == "public_selection":
            lines.append(_row(run))
    blind = [run for run in runs if run["partition"] == "blind_holdout"]
    if blind:
        lines.extend(
            [
                "",
                "## Blind confirmation",
                "",
                "The blind run was evaluated only after the public selection decision.",
                "",
                "| Arm | Variant | Resolved | Coverage | Mode-balanced score | Statuses |",
                "|---|---|---:|---:|---:|---|",
            ]
        )
        lines.extend(_row(run) for run in blind)
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"selection": selection, "runs": runs}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(write_report(root=args.root, output=args.output), sort_keys=True))


if __name__ == "__main__":
    main()
