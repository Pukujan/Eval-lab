"""Validate normalized outputs from EXP-20260920-010."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from eval_lab.schema import JudgePrediction

EXPECTED_MODELS = {
    "grok": "opencode/grok-4.6",
    "luna": "opencode/gpt-5.6-luna",
    "sol": "opencode/gpt-5.6-sol",
}


def _check_checksums(root: Path) -> None:
    for raw in (root / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, name = raw.split("  ", 1)
        actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
        if actual != digest:
            raise ValueError(f"checksum mismatch for {name}")


def _load_predictions(path: Path) -> list[JudgePrediction]:
    return [JudgePrediction.model_validate(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate(root: Path) -> dict[str, Any]:
    _check_checksums(root)
    results = json.loads((root / "results.json").read_text(encoding="utf-8"))
    if results["experiment_id"] != "EXP-20260920-010-multi-subscription-bakeoff":
        raise ValueError("wrong experiment ID")
    if results["benchmark_fingerprint"] != "18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5":
        raise ValueError("wrong benchmark fingerprint")
    expected_count = int(results["counts"]["provider_evaluation"])
    if expected_count <= 0:
        raise ValueError("provider pool is empty")
    reported_arms = results.get("arms")
    if not isinstance(reported_arms, dict) or not reported_arms:
        raise ValueError("results contain no attempted arms")
    unknown_arms = sorted(set(reported_arms) - set(EXPECTED_MODELS))
    if unknown_arms:
        raise ValueError(f"unexpected arm(s): {unknown_arms}")
    validated: dict[str, dict[str, int]] = {}
    for arm_id in sorted(reported_arms):
        model = EXPECTED_MODELS[arm_id]
        path = root / "predictions" / f"{arm_id}.jsonl"
        predictions = _load_predictions(path)
        if len(predictions) != expected_count:
            raise ValueError(f"{arm_id} has {len(predictions)} predictions, expected {expected_count}")
        if any(prediction.judge_id != model for prediction in predictions):
            raise ValueError(f"{arm_id} contains an unexpected model identity")
        if len({prediction.record_id for prediction in predictions}) != expected_count:
            raise ValueError(f"{arm_id} contains duplicate record IDs")
        if any(prediction.execution_status.value != "ok" and prediction.label is not None for prediction in predictions):
            raise ValueError(f"{arm_id} assigned a label to an unresolved provider call")
        validated[arm_id] = dict(Counter(prediction.execution_status.value for prediction in predictions))
    return {"experiment_id": results["experiment_id"], "status": results["status"], "arms": validated}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.experiment), sort_keys=True))


if __name__ == "__main__":
    main()
