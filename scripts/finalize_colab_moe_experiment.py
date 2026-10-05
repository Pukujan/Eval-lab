"""Assemble the EXP-20261005-031 Colab T4 MoE judge-arm experiment bundle.

Reads the raw label-only predictions produced on the Colab T4 by
``scripts/run_colab_moe_judge.py`` (staged verbatim under ``raw/``), normalizes
each row to the canonical prediction shape used by the local bakeoff, writes the
per-arm prediction files and ``run-config.json``, and then summarizes them into
``results.json`` and ``report.md`` with the same summarizer as the EXP-027 local
bakeoff.  It makes no model or provider calls and hand-types no metrics.

Usage:
    .venv\\Scripts\\python.exe scripts/finalize_colab_moe_experiment.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from report_local_decision_bakeoff import _markdown, summarize_predictions

from eval_lab.judges.local_decision_models import PROTOCOL_VERSION

EXPERIMENT_ID = "EXP-20261005-031-colab-t4-moe-judge-arms"
EXP015 = "EXP-20260921-015-grok-luna-qwen-bakeoff"
PARTITIONS = {"public": "public_selection", "blind": "blind_holdout"}
LABELS_BY_MODE = {"single": ["pass", "fail"], "pairwise": ["A", "B", "TIE"]}

LLAMA = {
    "build": "b11399",
    "version": "0.5.0-dev",
    "commit": "2ca15f540",
    "backend": "CUDA 12.8 prebuilt Linux release",
}

ARMS: tuple[dict[str, Any], ...] = (
    {
        "arm_id": "ornith-1.5-35b-a3b",
        "model_id": "bartowski/Ornith-1.5-35B-A3B-GGUF",
        "file": "Ornith-1.5-35B-A3B-IQ2_XXS.gguf",
        "architecture": "qwen35moe",
        "size_note": "MoE, 35B total / ~3B active (A3B)",
        "quant": "IQ2_XXS",
        "sha256": "14963c6830ae8287ad42a53c0fd87ca9fc67a8de8da1d18e3a076a348e96a32f",
        "size_bytes": 10255140512,
        "thinking": "disabled (chat_template_kwargs enable_thinking=false)",
    },
    {
        "arm_id": "maple-preview-20b-a1b",
        "model_id": "deepgrove/maple-preview-GGUF",
        "file": "maple-preview-TQ2_0-head-Q4_K.gguf",
        "architecture": "maple",
        "size_note": "MoE, 20B total / ~1B active (A1B)",
        "quant": "requantized TQ2_0 -> Q2_0 (Q4_K output head)",
        "sha256": "b8a69726d35af6d5ed9e161cf4fc86d851969bb15b49a374594b807fe5739ad8",
        "size_bytes": 5913366048,
        "source_file_sha256": "221f792cc9760d27a34f449b4229e258fa968a63bd4213993e45d9c0bb477a9e",
        "source_file_bytes": 5901782560,
        "thinking": "n/a (no reasoning channel)",
    },
)


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def _canonical(raw: dict[str, Any], arm: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw Colab runner row to the local-bakeoff prediction shape."""
    return {
        "record_id": raw["record_id"],
        "judge_id": arm["model_id"],
        "protocol_version": PROTOCOL_VERSION,
        "mode": raw.get("mode"),
        "legal_labels": raw.get("legal_labels"),
        "label": raw.get("label"),
        "probabilities": None,
        "raw_scores": None,
        "execution_status": raw["execution_status"],
        "latency_ms": raw.get("latency_ms"),
        "raw_output": raw.get("raw_output"),
        "usage": raw.get("usage"),
        "provider_metadata": {
            "provider": "colab-t4-llama-server",
            "arm_id": arm["arm_id"],
            "model_id": arm["model_id"],
            "model_file": arm["file"],
            "model_sha256": arm["sha256"],
            "quant": arm["quant"],
            "llama_build": LLAMA["build"],
            "llama_commit": LLAMA["commit"],
        },
        "error": raw.get("error"),
    }


def build(*, experiment_root: Path, records_path: Path) -> dict[str, Any]:
    pool_rows = _jsonl(records_path)
    model_revisions = {"models": list(ARMS)}
    (experiment_root / "model-revisions.json").write_text(
        json.dumps(model_revisions, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    partitions: dict[str, dict[str, Any]] = {}
    for partition, pool_partition in PARTITIONS.items():
        records = [row["record"] for row in pool_rows if row["partition"] == pool_partition]
        arms: dict[str, Any] = {}
        for arm in ARMS:
            raw_path = experiment_root / "raw" / partition / f"{arm['arm_id']}.jsonl"
            rows = [_canonical(row, arm) for row in _jsonl(raw_path)]
            out_dir = experiment_root / f"{partition}-predictions" / arm["arm_id"]
            prediction_path = out_dir / "predictions.jsonl"
            _write_jsonl(prediction_path, rows)
            (out_dir / "run-config.json").write_text(
                json.dumps(
                    {
                        "arm_id": arm["arm_id"],
                        "model_id": arm["model_id"],
                        "model_sha256": arm["sha256"],
                        "runner": "scripts/run_colab_moe_judge.py",
                        "runner_revision": f"llama.cpp {LLAMA['build']} ({LLAMA['commit']})",
                        "backend": LLAMA["backend"],
                        "grammar": "GBNF, exactly the legal labels",
                        "temperature": 0.0,
                        "max_tokens": 8,
                        "one_pass_per_record": True,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            arms[arm["arm_id"]] = summarize_predictions(
                records,
                rows,
                prediction_path=prediction_path,
                mode_key="mode",
                fixed_labels=None,
            )
        partitions[partition] = arms

    results = {
        "experiment_id": EXPERIMENT_ID,
        "dataset_fingerprint": "b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8",
        "primary_partition": "blind",
        "partitions": partitions,
        "model_arms": {arm["arm_id"]: arm for arm in ARMS},
        "calibration_policy": "label-only arm; no probabilities, so Brier/NLL/ECE are unavailable",
        "compute": {
            "host": "Google Colab free tier",
            "accelerator": "Tesla T4 (15,360 MiB, driver 580.82.07)",
            "runtime": "Ubuntu 24.04.4 LTS, 2 vCPU, 13.2 GB RAM",
            "server": f"llama.cpp {LLAMA['build']} ({LLAMA['commit']}), llama-server -ngl 99 -t 2",
        },
    }
    (experiment_root / "results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (experiment_root / "report.md").write_text(
        _markdown(EXPERIMENT_ID, partitions), encoding="utf-8"
    )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--experiment-root",
        type=Path,
        default=ROOT / "experiments" / EXPERIMENT_ID,
    )
    parser.add_argument(
        "--records",
        type=Path,
        default=ROOT / "experiments" / EXP015 / "records.jsonl",
    )
    args = parser.parse_args()
    results = build(experiment_root=args.experiment_root, records_path=args.records)
    print(
        json.dumps(
            {
                partition: {arm: summary["status_counts"] for arm, summary in arms.items()}
                for partition, arms in results["partitions"].items()
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
