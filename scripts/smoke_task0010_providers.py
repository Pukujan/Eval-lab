"""Smoke-test the three isolated TASK-0010 provider arms."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from eval_lab.escalation.providers import (
    OPENROUTER_PINNED_MODEL,
    OPENROUTER_ROLLING_MODEL,
    run_openrouter_jev,
    run_yolo_qwen,
)
from eval_lab.schema import JudgeRecord
from scripts.run_selective_escalation import _load_dotenv


def _records(path: Path, limit: int) -> list[JudgeRecord]:
    rows = path.read_text(encoding="utf-8").splitlines()
    return [JudgeRecord.model_validate(json.loads(row)["record"]) for row in rows[:limit]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=Path("benchmark/eval-lab-select-v0.1.0"))
    parser.add_argument("--output", type=Path, default=Path("experiments/EXP-20260920-009-selective-escalation/smoke"))
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--limit", type=int, default=1)
    args = parser.parse_args()
    if args.env_file:
        _load_dotenv(args.env_file)
    records = _records(args.benchmark / "records.jsonl", args.limit)
    args.output.mkdir(parents=True, exist_ok=True)
    arms = {
        "pinned": run_openrouter_jev(records, model=OPENROUTER_PINNED_MODEL),
        "rolling": run_openrouter_jev(records, model=OPENROUTER_ROLLING_MODEL),
        "qwen": run_yolo_qwen(records, base_url=os.getenv("QWEN_API_URL", "https://api.yolo-auto.com/v1")),
    }
    for name, predictions in arms.items():
        (args.output / f"{name}.jsonl").write_text(
            "".join(prediction.model_dump_json() + "\n" for prediction in predictions), encoding="utf-8"
        )
    print(
        json.dumps(
            {
                name: sorted({prediction.execution_status.value for prediction in predictions})
                for name, predictions in arms.items()
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
