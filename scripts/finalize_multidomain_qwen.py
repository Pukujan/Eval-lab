"""Finalize the frozen public and blind Qwen reports into one experiment bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads((path / "results.json").read_text(encoding="utf-8"))


def _fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def finalize(output: Path, public: Path, blind: Path) -> dict[str, Any]:
    if (output / "results.json").exists() or (output / "report.md").exists():
        raise FileExistsError(f"refusing to overwrite finalized files in {output}")
    public_results = _load(public)
    blind_results = _load(blind)
    results = {
        "experiment_id": "EXP-20260921-013-qwen-multidomain-holdout",
        "status": "completed",
        "provider": "yolo-auto",
        "model": "qwen3.8-flash",
        "pool_fingerprint": "b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8",
        "blind_record_ids_fingerprint": "409428fc71b447d0114dd7a1929cbed34269a4318ef249c108582b70069d8d61",
        "probabilities_available": False,
        "calibration_status": "unavailable: provider returned labels without verifiable probabilities/logprobs",
        "partitions": {
            "public_selection": public_results,
            "blind_holdout": blind_results,
        },
        "gold_not_used_for_provider_request": True,
    }
    (output / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    public_metrics = public_results["metrics"]
    blind_metrics = blind_results["metrics"]
    datasets = sorted(set(public_metrics["by_dataset"]) | set(blind_metrics["by_dataset"]))
    lines = [
        "# EXP-20260921-013 — Qwen multidomain holdout",
        "",
        "Provider: `yolo-auto`; model: `qwen3.8-flash`; transport: one frozen record per streaming request.",
        "",
        "The public-selection and blind-holdout partitions were frozen before provider execution. Gold labels were used only after provider execution for objective scoring. Provider failures remain unresolved and no fallback labels were fabricated.",
        "",
        f"Pool fingerprint: `{results['pool_fingerprint']}`; blind record-ID fingerprint: `{results['blind_record_ids_fingerprint']}`.",
        "",
        "| Dataset | Public n/resolved | Public accuracy | Blind n/resolved | Blind accuracy | Blind unresolved | Blind p95 ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for dataset in datasets:
        public_value = public_metrics["by_dataset"].get(dataset)
        blind_value = blind_metrics["by_dataset"].get(dataset)
        lines.append(
            f"| `{dataset}` | "
            f"{public_value['records']}/{public_value['resolved'] if public_value else 'NA'} | "
            f"{_fmt(public_value['accuracy'] if public_value else None)} | "
            f"{blind_value['records']}/{blind_value['resolved'] if blind_value else 'NA'} | "
            f"{_fmt(blind_value['accuracy'] if blind_value else None)} | "
            f"{_fmt(blind_value['unresolved_rate'] if blind_value else None)} | "
            f"{_fmt(blind_value['latency']['p95_ms'] if blind_value else None)} |"
        )
    lines.extend(
        [
            "",
            f"Public selection: `{public_metrics['correct']}/{public_metrics['resolved']}` correct among resolved records; unresolved rate `{public_metrics['unresolved_rate']:.4f}`.",
            f"Blind holdout: `{blind_metrics['correct']}/{blind_metrics['resolved']}` correct among resolved records; unresolved rate `{blind_metrics['unresolved_rate']:.4f}`.",
            "",
            "Calibration metrics requiring probabilities/logprobs are unavailable for this Qwen route. This experiment evaluates label accuracy and operational reliability; it does not claim calibrated Qwen confidence.",
            "",
            "See `limitations.md` for threats to validity and `qwen-public-report-20260921/report.md` and `qwen-blind-report-20260921/report.md` for full per-partition metrics and Wilson intervals.",
        ]
    )
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "experiment_id": results["experiment_id"],
        "status": results["status"],
        "public": public_metrics["status_counts"],
        "blind": blind_metrics["status_counts"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("experiments/EXP-20260921-013-qwen-multidomain-holdout"))
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--blind", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(finalize(args.output, args.public, args.blind), sort_keys=True))


if __name__ == "__main__":
    main()
