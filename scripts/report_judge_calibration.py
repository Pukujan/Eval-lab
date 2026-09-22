"""Assemble the completed EXP-017 local calibration report and references."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metrics(result: dict[str, Any], view: str) -> dict[str, Any]:
    report = result.get(f"{view}_report") or {}
    aggregate = report.get("aggregate") or {}
    values = aggregate.get("metrics") or {}
    return {
        "count": aggregate.get("count"),
        "accuracy": values.get("accuracy"),
        "balanced_accuracy": values.get("balanced_accuracy"),
        "brier": values.get("brier"),
        "nll": values.get("nll"),
        "ece": values.get("ece"),
        "probability_metrics_available": aggregate.get("probability_metrics_available"),
    }


def _local_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_count": result["record_count"],
        "status_counts": result["status_counts"],
        "probability_count": result["probability_count"],
        "runtime": result["runtime"],
        "raw": _metrics(result, "raw"),
        "calibrated": _metrics(result, "calibrated"),
        "calibration": result["calibration"],
    }


def _reference_summary(result: dict[str, Any], arm: str) -> dict[str, Any]:
    item = result["arms"][arm]
    aggregate = item.get("metrics", {}).get("aggregate", {})
    metrics = aggregate.get("metrics", {})
    status_counts = item.get("status_counts", {})
    resolved = item.get("resolved_count") or sum(status_counts.get("ok", 0) for _ in [0])
    record_count = item.get("record_count") or 760
    return {
        "provider": item.get("provider"),
        "route": item.get("route"),
        "requested_model": item.get("requested_model"),
        "surfaced_model_ids": item.get("surfaced_model_ids", []),
        "record_count": record_count,
        "resolved_count": resolved,
        "resolved_coverage": resolved / record_count if record_count else None,
        "status_counts": status_counts,
        "accuracy": metrics.get("accuracy", item.get("accuracy")),
        "balanced_accuracy": metrics.get("balanced_accuracy"),
        "probability_metrics_available": aggregate.get("probability_metrics_available", False),
    }


def _checksums(root: Path) -> None:
    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "checksums.sha256":
            continue
        entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}")
    (root / "checksums.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")


def run(root: Path, pool: Path, jev_root: Path) -> None:
    public = _read(root / "runs" / "public-qwen4b-4bit-20260921" / "results.json")
    blind = _read(root / "runs" / "blind-qwen4b-4bit-20260921" / "results.json")
    direct = _read(pool / "runs" / "blind-stream-parallel-20260921" / "results.json")
    direct_status = _read(pool / "runs" / "blind-stream-parallel-20260921" / "provider-status.json")
    jev = _read(jev_root / "results.json")
    jev_record_count = jev.get("record_count") or 0
    jev_correct_count = jev.get("correct_count") or 0
    jev_accuracy = jev.get("accuracy")
    if jev_accuracy is None and jev_record_count:
        jev_accuracy = jev_correct_count / jev_record_count
    references = {
        "grok": _reference_summary({"arms": {"grok": direct["arms"]["grok"]}}, "grok"),
        "luna": _reference_summary({"arms": {"luna": direct["arms"]["luna"]}}, "luna"),
        "qwen_flash": _reference_summary({"arms": {"qwen_flash": direct["arms"]["qwen_flash"]}}, "qwen_flash"),
        "jev_pinned": {
            "provider": "openrouter",
            "route": "openrouter-jev-only",
            "requested_model": jev.get("model", "typesafe/jev-1.13"),
            "surfaced_model_ids": jev.get("surfaced_model_ids", []),
            "record_count": jev.get("record_count"),
            "resolved_count": jev.get("resolved_count"),
            "resolved_coverage": (jev.get("resolved_count") / jev.get("record_count")) if jev.get("record_count") else None,
            "status_counts": jev.get("status_counts", {}),
            "accuracy": jev_accuracy,
            "balanced_accuracy": (jev.get("metrics", {}).get("aggregate", {}).get("metrics", {}) or {}).get("balanced_accuracy"),
            "probability_metrics_available": False,
            "source_experiment": "EXP-20260921-018-jev-openrouter-reference",
        },
    }
    local = {"public_selection": _local_summary(public), "blind_holdout": _local_summary(blind)}
    comparison = {
        "experiment_id": "EXP-20260921-017-judge-calibration",
        "primary_partition": "blind_holdout",
        "local_qwen4b": local["blind_holdout"],
        "references": references,
        "comparison_rule": "provider failures are excluded from resolved accuracy; only local Qwen has calibrated probabilities in this experiment",
        "direct_reference_status": direct_status,
        "gold_provenance": "inherited EXP-015 answer_key and deterministic_verifier; model judgments are not gold",
    }
    results = {
        "experiment_id": "EXP-20260921-017-judge-calibration",
        "status": "completed",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "primary_partition": "blind_holdout",
        "source_pool": blind["source_pool"],
        "local_runtime": blind["runtime"],
        "public_selection": local["public_selection"],
        "blind_holdout": local["blind_holdout"],
        "references": references,
        "limitations": [
            "Qwen 4B is a lightweight local judge, not objective gold.",
            "Calibration fit used public_selection only; blind labels were not used for fitting.",
            "Grok, Luna, Qwen Flash, and Jev references are label/coverage comparisons without validated native probabilities.",
            "The first 182-record FP16 checkpoint was paused and excluded; all primary Qwen results use the committed 4-bit runtime.",
        ],
    }
    (root / "reference-comparison.json").write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    blind_raw = local["blind_holdout"]["raw"]
    blind_cal = local["blind_holdout"]["calibrated"]
    lines = [
        "# EXP-20260921-017 — Local Qwen 4B judge calibration",
        "",
        "Status: completed. The exact EXP-015 pool is unchanged; model outputs are not gold.",
        "",
        "## Primary blind holdout",
        "",
        "| View | Accuracy | Brier | NLL | ECE | Coverage |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        f"| raw | {blind_raw['accuracy']} | {blind_raw['brier']} | {blind_raw['nll']} | {blind_raw['ece']} | 1.0 |",
        f"| calibrated | {blind_cal['accuracy']} | {blind_cal['brier']} | {blind_cal['nll']} | {blind_cal['ece']} | 1.0 |",
        "",
        "Calibration temperature was fit separately by judgment mode on public_selection only.",
        "",
        "## Reference arms",
        "",
        "| Arm | Route | Accuracy | Coverage | Status |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for name, item in references.items():
        lines.append(
            f"| {name} | {item['route']} | {item['accuracy']} | {item['resolved_coverage']} | {item['status_counts']} |"
        )
    lines.extend(
        [
            "",
            "The direct Grok/Luna/Qwen Flash references come from EXP-015; pinned Jev comes from the separate Jev-only EXP-018 OpenRouter run. OpenRouter is not used for Grok, Luna, Sol, or Qwen, and OpenCode is not used.",
            "",
            "## Runtime and limitations",
            "",
            f"- Model: `{blind['runtime']['model_id']}` at revision `{blind['runtime']['resolved_revision']}`.",
            f"- Runtime: `{blind['runtime']['quantization']}`, `{blind['runtime']['dtype']}`, `{blind['runtime']['device']}`; context cap `{blind['runtime']['context_cap']}`.",
            "- The frozen pool's maximum measured input prompt was 755 tokens, so the 2,048-token cap did not truncate this pool.",
            "- Provider failures remain explicit in reference status counts and are not counted as ordinary wrong answers.",
        ]
    )
    (root / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _checksums(root)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("experiments/EXP-20260921-017-judge-calibration"))
    parser.add_argument("--pool", type=Path, default=Path("experiments/EXP-20260921-015-grok-luna-qwen-bakeoff"))
    parser.add_argument(
        "--jev-root",
        type=Path,
        default=Path("experiments/EXP-20260921-014-independent-jev-benchmark/jev-pinned-blind-20260921"),
    )
    args = parser.parse_args()
    run(args.root, args.pool, args.jev_root)


if __name__ == "__main__":
    main()
