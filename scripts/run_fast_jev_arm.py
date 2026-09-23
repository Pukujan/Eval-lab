"""Run a bounded, checkpointed concurrent Jev Decisions arm."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval_lab.escalation.providers import OPENROUTER_PINNED_MODEL, run_openrouter_jev
from eval_lab.schema import ExecutionStatus, JudgePrediction, JudgeRecord

EXPERIMENT_ID = "EXP-20260922-022-fast-provider-wave"
SOURCE_POOL = Path("experiments") / "EXP-20260921-015-grok-luna-qwen-bakeoff"


def _load_dotenv(path: Path | None) -> dict[str, str]:
    values: dict[str, str] = {}
    if path is None or not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _load_records(pool: Path, partition: str, limit: int) -> tuple[list[dict[str, Any]], list[JudgeRecord]]:
    rows = [
        json.loads(line)
        for line in (pool / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected = [row for row in rows if partition == "all" or row["partition"] == partition]
    if limit:
        selected = selected[:limit]
    records = [JudgeRecord.model_validate(row["record"]) for row in selected]
    if not records or len({record.record_id for record in records}) != len(records):
        raise ValueError("selected pool is empty or contains duplicate IDs")
    return selected, records


def _prediction_error(record: JudgeRecord, model: str, error_type: str) -> JudgePrediction:
    return JudgePrediction(
        record_id=record.record_id,
        judge_id=model,
        protocol_version="eval-lab-system-one-v1",
        execution_status=ExecutionStatus.PROVIDER_ERROR,
        latency_ms=0.0,
        provider_metadata={"provider": "openrouter", "model": model},
        error={"type": error_type},
    )


def _run(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.output)
    if output.exists() and any(output.iterdir()) and not args.resume:
        raise FileExistsError(f"refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    prediction_path = output / "predictions.jsonl"
    existing: dict[str, JudgePrediction] = {}
    if args.resume and prediction_path.is_file():
        for line in prediction_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                prediction = JudgePrediction.model_validate_json(line)
                if prediction.record_id in existing:
                    raise ValueError("resume checkpoint contains duplicate record IDs")
                existing[prediction.record_id] = prediction

    pool = Path(args.pool)
    _rows, records = _load_records(pool, args.partition, args.limit)
    expected = {record.record_id for record in records}
    if not set(existing).issubset(expected):
        raise ValueError("resume checkpoint contains an out-of-pool record ID")
    environment = {**_load_dotenv(Path(args.env_file) if args.env_file else None), **os.environ}
    api_key = environment.get("OPENROUTER_API_KEY")
    pending = [record for record in records if record.record_id not in existing]
    started = time.perf_counter()

    def evaluate(record: JudgeRecord) -> JudgePrediction:
        if not api_key:
            return _prediction_error(record, args.model, "missing_api_key")
        try:
            return run_openrouter_jev(
                [record],
                model=args.model,
                api_key=api_key,
                client=None,
                timeout=args.timeout,
            )[0]
        except Exception as exc:  # noqa: BLE001 - preserve one provider fault per record
            return _prediction_error(record, args.model, type(exc).__name__)

    prediction_path.touch(exist_ok=True)
    with prediction_path.open("a", encoding="utf-8") as handle, ThreadPoolExecutor(
        max_workers=args.workers
    ) as executor:
        futures = {executor.submit(evaluate, record): record.record_id for record in pending}
        for future in as_completed(futures):
            prediction = future.result()
            existing[prediction.record_id] = prediction
            handle.write(prediction.model_dump_json() + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    if set(existing) != expected:
        raise RuntimeError("Jev run did not produce one status per selected record")
    ordered = [existing[record.record_id] for record in records]
    statuses = dict(sorted(Counter(prediction.execution_status.value for prediction in ordered).items()))
    source_manifest = json.loads((pool / "pool-manifest.json").read_text(encoding="utf-8"))
    results = {
        "experiment_id": args.experiment_id,
        "run_id": output.name,
        "provider": "openrouter",
        "requested_model": args.model,
        "partition": args.partition,
        "record_count": len(records),
        "workers": args.workers,
        "status_counts": statuses,
        "resolved_count": sum(prediction.execution_status is ExecutionStatus.OK for prediction in ordered),
        "elapsed_seconds": time.perf_counter() - started,
        "source_pool": {
            "records_fingerprint": source_manifest["records_fingerprint"],
            "blind_record_ids_fingerprint": source_manifest["blind_record_ids_fingerprint"],
            "typed_question_spec_fingerprint": source_manifest["typed_question_spec_fingerprint"],
        },
        "gold_not_used_for_provider_request": True,
        "created_at_utc": datetime.now(UTC).isoformat(),
    }
    (output / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "report.md").write_text(
        "\n".join(
            [
                f"# {args.experiment_id} — {output.name}",
                "",
                f"Partition: `{args.partition}`; records: `{len(records)}`; workers: `{args.workers}`.",
                f"Status counts: `{statuses}`.",
                "",
                "Jev provider output is a label-only external judgment; provider failures and rate limits remain unresolved.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    checksums = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "checksums.sha256":
            checksums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(output).as_posix()}")
    (output / "checksums.sha256").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, default=SOURCE_POOL)
    parser.add_argument("--experiment-id", default=EXPERIMENT_ID)
    parser.add_argument("--partition", choices=("public_selection", "blind_holdout", "all"), required=True)
    parser.add_argument("--model", default=OPENROUTER_PINNED_MODEL)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.limit < 0 or args.workers <= 0:
        raise SystemExit("--limit must be non-negative and --workers must be positive")
    print(json.dumps(_run(args), sort_keys=True))


if __name__ == "__main__":
    main()
