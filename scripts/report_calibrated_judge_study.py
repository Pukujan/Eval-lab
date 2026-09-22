"""Build the EXP-019 offline calibration and independent-judge report."""

from __future__ import annotations

import argparse
import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from eval_lab.metrics.classification import classification_metrics

EXPERIMENT_ID = "EXP-20260921-019-calibrated-judge-study"
BLIND_PARTITION = "blind_holdout"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _load_pool(path: Path) -> dict[str, dict[str, Any]]:
    pool: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        if row["partition"] != BLIND_PARTITION:
            continue
        record = row["record"]
        record_id = record["record_id"]
        if record_id in pool:
            raise ValueError(f"duplicate blind record {record_id}")
        pool[record_id] = {
            "gold_label": record["gold"]["label"],
            "dataset": row["dataset"],
            "mode": record["mode"],
            "variant": record.get("perturbation", {}).get("variant"),
            "record": record,
        }
    if len(pool) != 760:
        raise ValueError(f"expected 760 blind records, found {len(pool)}")
    return pool


def _prediction_from_row(row: dict[str, Any]) -> dict[str, Any]:
    prediction = row.get("prediction")
    if not isinstance(prediction, dict):
        prediction = row
    record_id = prediction.get("record_id", row.get("record_id"))
    if not isinstance(record_id, str):
        raise TypeError("prediction row has no record_id")
    return prediction | {"record_id": record_id}


def _load_predictions(path: Path) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        prediction = _prediction_from_row(row)
        record_id = prediction["record_id"]
        if record_id in output:
            raise ValueError(f"duplicate prediction {record_id} in {path}")
        output[record_id] = prediction
    return output


def _merge_retry(primary: dict[str, dict[str, Any]], retry: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    merged = dict(primary)
    for record_id, prediction in retry.items():
        if record_id in merged and merged[record_id].get("execution_status") == "ok":
            raise ValueError(f"retry would overwrite successful primary prediction {record_id}")
        merged[record_id] = prediction
    return merged


def _resolved(predictions: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {record_id: row for record_id, row in predictions.items() if row.get("execution_status") == "ok"}


def _wilson(successes: int, trials: int) -> dict[str, float] | None:
    if trials == 0:
        return None
    z = 1.959963984540054
    estimate = successes / trials
    denominator = 1.0 + z * z / trials
    center = (estimate + z * z / (2.0 * trials)) / denominator
    margin = z * math.sqrt(estimate * (1.0 - estimate) / trials + z * z / (4.0 * trials * trials)) / denominator
    return {"lower": max(0.0, center - margin), "upper": min(1.0, center + margin)}


def _arm_summary(predictions: dict[str, dict[str, Any]], pool: dict[str, dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(row.get("execution_status", "missing") for row in predictions.values())
    resolved = _resolved(predictions)
    correct = sum(row.get("label") == pool[record_id]["gold_label"] for record_id, row in resolved.items())
    by_domain: dict[str, dict[str, int]] = defaultdict(lambda: {"resolved": 0, "correct": 0})
    by_mode: dict[str, dict[str, int]] = defaultdict(lambda: {"resolved": 0, "correct": 0})
    label_counts = Counter()
    true_labels: list[str] = []
    predicted_labels: list[str] = []
    for record_id, row in resolved.items():
        metadata = pool[record_id]
        domain = metadata["dataset"]
        mode = metadata["mode"]
        is_correct = row.get("label") == metadata["gold_label"]
        by_domain[domain]["resolved"] += 1
        by_domain[domain]["correct"] += int(is_correct)
        by_mode[mode]["resolved"] += 1
        by_mode[mode]["correct"] += int(is_correct)
        label_counts[str(row.get("label"))] += 1
        true_labels.append(str(metadata["gold_label"]))
        predicted_labels.append(str(row.get("label")))
    domains = {
        domain: {
            **counts,
            "accuracy": counts["correct"] / counts["resolved"] if counts["resolved"] else None,
        }
        for domain, counts in sorted(by_domain.items())
    }
    modes = {
        mode: {
            **counts,
            "accuracy": counts["correct"] / counts["resolved"] if counts["resolved"] else None,
        }
        for mode, counts in sorted(by_mode.items())
    }
    return {
        "prediction_count": len(predictions),
        "resolved_count": len(resolved),
        "correct_count": correct,
        "accuracy": correct / len(resolved) if resolved else None,
        "accuracy_wilson_95": _wilson(correct, len(resolved)),
        "classification_metrics": classification_metrics(
            true_labels,
            predicted_labels,
            class_order=list(dict.fromkeys([*true_labels, *predicted_labels])),
        )
        if resolved
        else None,
        "status_counts": dict(sorted(statuses.items())),
        "label_counts": dict(sorted(label_counts.items())),
        "by_domain": domains,
        "by_mode": modes,
    }


def _agreement(left: dict[str, dict[str, Any]], right: dict[str, dict[str, Any]]) -> dict[str, Any]:
    common = sorted(set(_resolved(left)) & set(_resolved(right)))
    matches = sum(left[record_id].get("label") == right[record_id].get("label") for record_id in common)
    return {
        "comparable_count": len(common),
        "agreement_count": matches,
        "agreement_rate": matches / len(common) if common else None,
    }


def _load_calibration_summary(path: Path) -> dict[str, Any]:
    results = _read_json(path)
    output: dict[str, Any] = {}
    for partition in ("public_selection", "blind_holdout"):
        item = results[partition]
        output[partition] = {
            "raw": item["raw"],
            "calibrated": item["calibrated"],
            "calibration_fit": item.get("calibration"),
        }
    return output


def _jev_robustness(path: Path) -> dict[str, Any]:
    results = _read_json(path)
    return {
        "repeatability_rate": results.get("repeatability_rate"),
        "option_order_agreement_rate": results.get("option_order_agreement_rate"),
        "rubric_paraphrase_agreement_rate": results.get("rubric_paraphrase_agreement_rate"),
        "option_order_resolved": results.get("option_order_resolved"),
        "rubric_paraphrase_resolved": results.get("rubric_paraphrase_resolved"),
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# {EXPERIMENT_ID}",
        "",
        "This report studies rubric-grounded judge construction, split-safe confidence calibration, and independent head-to-head comparison.",
        "",
        "Luna and Sol are excluded from the primary study under the vendor-independent orchestrator policy. Their historical artifacts are not used in the tables, pairwise analyses, calibration, adjudication, or conclusions.",
        "",
        "## Method",
        "",
        "The report reuses the exact EXP-015 pool and typed System-One packet. Gold labels come from benchmark answer keys and deterministic verifiers. Local Qwen 4B probabilities are calibrated with scalar temperature scaling fit only on public-selection records, separately for single and pairwise judgments. External arms are label-only unless they provide a validated probability map; no probability metrics are invented from prose or labels.",
        "",
        "## Blind head-to-head results",
        "",
        "| Arm | Resolved labels | Accuracy | Balanced accuracy | Macro F1 | 95% Wilson interval |",
        "|---|---:|---:|---:|---:|---|",
    ]
    display_names = {"grok": "Grok Build", "jev": "Jev", "qwen_flash": "Qwen Flash", "local_qwen4b": "Local Qwen 4B"}
    for arm in ("grok", "jev", "qwen_flash", "local_qwen4b"):
        item = report["arms"][arm]
        interval = item["accuracy_wilson_95"] or {}
        metrics = item["classification_metrics"] or {}
        interval_text = f"[{interval.get('lower', 0):.4f}, {interval.get('upper', 0):.4f}]" if interval else "—"
        lines.append(
            f"| {display_names[arm]} | {item['resolved_count']} | {item['accuracy']:.4f} | {metrics.get('balanced_accuracy', 0):.4f} | {metrics.get('macro_f1', 0):.4f} | {interval_text} |"
        )
    diagnostic = report.get("grok_diagnostic")
    diagnostic_line = "No new direct Grok diagnostic was included."
    if diagnostic:
        diagnostic_line = (
            f"A separate direct Grok Build diagnostic used `{diagnostic['record_count']}` records with "
            f"streaming enabled, returned `{diagnostic['status_counts']}`, and surfaced "
            f"`{diagnostic['surfaced_model_ids']}`. It reproduced the same mode asymmetry: "
            f"single accuracy `{diagnostic['by_mode'].get('single', {}).get('accuracy')}` and "
            f"pairwise accuracy `{diagnostic['by_mode'].get('pairwise', {}).get('accuracy')}`."
        )
    lines.extend(["", "Execution status is retained in the machine-readable artifact for auditability; it is not treated as a model-quality outcome in this study.", "", "## Protocol diagnostics", "", f"Grok's blind labels are `{report['arms']['grok']['label_counts']}`. Its single-record accuracy is `{report['arms']['grok']['by_mode'].get('single', {}).get('accuracy')}` and its pairwise accuracy is `{report['arms']['grok']['by_mode'].get('pairwise', {}).get('accuracy')}`. This mode asymmetry is retained as a protocol diagnostic rather than generalized into a claim about all Grok capability.", diagnostic_line, "", "## Same-record agreement", "", "| Pair | Comparable | Agreement |", "|---|---:|---:|"])
    for pair, item in report["agreement"].items():
        lines.append(f"| {pair.replace('__vs__', ' vs. ')} | {item['comparable_count']} | {item['agreement_rate']:.4f} |")
    lines.extend(["", "## Calibration results", "", "Calibration changes confidence values, not selected labels. The blind local-Qwen result is:", "", "| View | Accuracy | Brier | NLL | ECE |", "|---|---:|---:|---:|---:|"])
    blind = report["calibration"]["blind_holdout"]
    for view in ("raw", "calibrated"):
        metrics = blind[view]
        lines.append(
            f"| {view} | {metrics['accuracy']:.4f} | {metrics['brier']:.4f} | {metrics['nll']:.4f} | {metrics['ece']:.4f} |"
        )
    modes = blind["calibration_fit"]["modes"]
    lines.extend(
        [
            "",
            f"Fitted temperatures: single `{modes['single']['artifact']['parameters']['temperature']:.6f}`; pairwise `{modes['pairwise']['artifact']['parameters']['temperature']:.6f}`.",
            "Fitted temperatures are recorded in the calibration artifact and were fit on public-selection labels only. Accuracy and label metrics are unchanged by temperature scaling; Brier, NLL, and ECE are the calibration outcomes.",
            "",
            "## Rubric/protocol robustness",
            "",
        ]
    )
    robustness = report["jev_robustness"]
    lines.append(
        f"Jev's existing robustness canary reports repeatability `{robustness['repeatability_rate']}`, option-order agreement `{robustness['option_order_agreement_rate']}`, and rubric-paraphrase agreement `{robustness['rubric_paraphrase_agreement_rate']}`. These are descriptive robustness checks, not objective gold substitutions."
    )
    lines.extend(["", "## Limitations", "", "The head-to-head external arms do not expose validated native probabilities in the completed artifacts, so their calibration cannot be ranked. The local-Qwen calibration result is therefore a method demonstration, not evidence that every provider route has calibrated confidence. The study measures objective typed decisions and does not establish universal subjective human-evaluation quality.", ""])
    return "\n".join(lines)


def build_report(repo: Path) -> dict[str, Any]:
    exp015 = repo / "experiments" / "EXP-20260921-015-grok-luna-qwen-bakeoff"
    exp014 = repo / "experiments" / "EXP-20260921-014-independent-jev-benchmark"
    exp016 = repo / "experiments" / "EXP-20260921-016-qwen-rate-limit-retry"
    exp017 = repo / "experiments" / "EXP-20260921-017-judge-calibration"
    diagnostic_dir = repo / "experiments" / EXPERIMENT_ID / "diagnostics" / "grok-mode-check-20260921"
    pool = _load_pool(exp015 / "records.jsonl")
    blind = exp015 / "runs" / "blind-stream-parallel-20260921" / "predictions"
    grok = _load_predictions(blind / "grok.jsonl")
    qwen_primary = _load_predictions(blind / "qwen_flash.jsonl")
    qwen_retry = _load_predictions(exp016 / "runs" / "retry-20260921" / "predictions" / "qwen_flash.jsonl")
    qwen = _merge_retry(qwen_primary, qwen_retry)
    jev = _load_predictions(exp014 / "jev-pinned-blind-20260921" / "predictions.jsonl")
    local_qwen = _load_predictions(exp017 / "runs" / "blind-qwen4b-4bit-20260921" / "raw_predictions.jsonl")

    arms = {"grok": grok, "jev": jev, "qwen_flash": qwen, "local_qwen4b": local_qwen}
    report: dict[str, Any] = {
        "experiment_id": EXPERIMENT_ID,
        "status": "completed",
        "purpose": "calibrated judge construction and independent head-to-head comparison",
        "source_pool": {
            "experiment": "EXP-015",
            "fingerprint": "b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8",
            "blind_record_count": len(pool),
        },
        "included_arms": ["grok", "jev", "qwen_flash", "local_qwen4b"],
        "excluded_arms": {
            "luna": "vendor-independent orchestrator comparison policy",
            "sol": "vendor-independent orchestrator comparison policy",
        },
        "arms": {name: _arm_summary(predictions, pool) for name, predictions in arms.items()},
        "agreement": {
            f"{left}__vs__{right}": _agreement(arms[left], arms[right])
            for left, right in itertools.combinations(arms, 2)
        },
        "calibration": _load_calibration_summary(exp017 / "results.json"),
        "jev_robustness": _jev_robustness(exp014 / "perturbations-pinned-final-20260921" / "results.json"),
        "grok_diagnostic": None,
        "source_artifacts": {
            "grok": "EXP-015/runs/blind-stream-parallel-20260921/predictions/grok.jsonl",
            "jev": "EXP-014/jev-pinned-blind-20260921/predictions.jsonl",
            "qwen_flash_primary": "EXP-015/runs/blind-stream-parallel-20260921/predictions/qwen_flash.jsonl",
            "qwen_flash_retry": "EXP-016/runs/retry-20260921/predictions/qwen_flash.jsonl",
            "local_qwen4b": "EXP-017/runs/blind-qwen4b-4bit-20260921/raw_predictions.jsonl",
        },
        "probability_policy": "Only validated native/local probability maps receive Brier, NLL, ECE, or risk/coverage metrics.",
        "execution_policy": "Provider execution states remain audit metadata and are not a research outcome.",
    }
    diagnostic_results = diagnostic_dir / "results.json"
    diagnostic_predictions = diagnostic_dir / "predictions" / "grok.jsonl"
    if diagnostic_results.is_file() and diagnostic_predictions.is_file():
        diagnostic_payload = _read_json(diagnostic_results)
        diagnostic_arm = diagnostic_payload["arms"]["grok"]
        report["grok_diagnostic"] = {
            "record_count": diagnostic_payload["record_count"],
            "status_counts": diagnostic_arm["status_counts"],
            "surfaced_model_ids": diagnostic_arm["surfaced_model_ids"],
            "streaming": diagnostic_payload["execution"]["streaming"],
            "stream_format": diagnostic_payload["execution"]["stream_formats"]["grok"],
            "by_mode": _arm_summary(_load_predictions(diagnostic_predictions), pool)["by_mode"],
        }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("experiments") / EXPERIMENT_ID)
    args = parser.parse_args()
    repo = args.repo.resolve()
    output = args.output if args.output.is_absolute() else repo / args.output
    output.mkdir(parents=True, exist_ok=True)
    report = build_report(repo)
    (output / "results.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "report.md").write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({"experiment_id": EXPERIMENT_ID, "output": str(output), "status": "completed"}, sort_keys=True))


if __name__ == "__main__":
    main()
