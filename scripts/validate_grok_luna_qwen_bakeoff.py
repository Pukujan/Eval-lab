"""Validate one normalized run from EXP-20260921-015."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from eval_lab.schema import ExecutionStatus, JudgePrediction

EXPERIMENT_ID = "EXP-20260921-015-grok-luna-qwen-bakeoff"


def _check_checksums(root: Path) -> None:
    checksum_path = root / "checksums.sha256"
    if not checksum_path.is_file():
        raise ValueError("run is missing checksums.sha256")
    for raw in checksum_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, name = raw.split("  ", 1)
        path = root / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"checksum mismatch for {name}")


def _load_predictions(path: Path) -> list[JudgePrediction]:
    return [
        JudgePrediction.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate(root: Path) -> dict[str, Any]:
    _check_checksums(root)
    results = json.loads((root / "results.json").read_text(encoding="utf-8"))
    if results.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("wrong experiment ID")
    record_count = int(results["record_count"])
    if record_count <= 0 or not results.get("record_ids_unique"):
        raise ValueError("run has no unique matched records")
    arms = results.get("arms")
    if not isinstance(arms, dict) or not arms:
        raise ValueError("run contains no attempted arms")
    status_payload = json.loads((root / "provider-status.json").read_text(encoding="utf-8"))
    validated: dict[str, dict[str, int]] = {}
    for arm_id, summary in arms.items():
        path = root / "predictions" / f"{arm_id}.jsonl"
        predictions = _load_predictions(path)
        if len(predictions) != record_count:
            raise ValueError(f"{arm_id} has {len(predictions)} predictions; expected {record_count}")
        if len({prediction.record_id for prediction in predictions}) != record_count:
            raise ValueError(f"{arm_id} contains duplicate record IDs")
        if any(
            prediction.label is not None and prediction.execution_status is not ExecutionStatus.OK
            for prediction in predictions
        ):
            raise ValueError(f"{arm_id} assigned a label to an unresolved execution")
        counts = dict(sorted(Counter(prediction.execution_status.value for prediction in predictions).items()))
        if counts != summary["status_counts"]:
            raise ValueError(f"{arm_id} status counts disagree between results and predictions")
        status_arm = status_payload.get("arms", {}).get(arm_id)
        if status_arm is None or status_arm["status_counts"] != counts:
            raise ValueError(f"{arm_id} provider status is missing or inconsistent")
        surfaced = sorted(
            {
                model_id
                for prediction in predictions
                for model_id in prediction.provider_metadata.get("surfaced_model_ids", [])
            }
        )
        if surfaced != summary["surfaced_model_ids"]:
            raise ValueError(f"{arm_id} surfaced model IDs disagree with results")
        validated[arm_id] = counts
    return {
        "experiment_id": EXPERIMENT_ID,
        "run_id": results["run_id"],
        "partition": results["partition"],
        "record_count": record_count,
        "arms": validated,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.experiment), sort_keys=True))


if __name__ == "__main__":
    main()
