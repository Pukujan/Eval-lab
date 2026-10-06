"""Run one bounded, checkpointed Jev closed-set classifier arm per GLEIF family.

Each arm sends one family's blind requests to ``typesafe/jev-1.13`` through the
authorized Decisions route with the family's closed label set and per-label
criteria, then records exactly one terminal status per request. Provider
failures and rate limits remain execution statuses and are never turned into
labels. The runner never reads a gold label: it joins predictions to gold only
later, in ``scripts/report_gleif_classifier.py``.
"""

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
from eval_lab.schema import (
    ExecutionStatus,
    GoldLabel,
    GoldProvenance,
    JudgePrediction,
    JudgeRecord,
    JudgmentMode,
    RubricCriterion,
    Split,
)

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ID = "EXP-20261005-032-gleif-classifier"
EXPERIMENT_DIR = ROOT / "experiments" / EXPERIMENT_ID
# Only a resolved label is terminal for recovery purposes; every other status is
# a provider fault that a resumed run may spend its recovery budget on.
_TERMINAL_OK = frozenset({ExecutionStatus.OK})


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


def _load_requests(path: Path, limit: int) -> tuple[list[dict[str, Any]], list[JudgeRecord]]:
    """Rebuild provider-facing records from the gold-free request file."""

    rows = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if limit:
        rows = rows[:limit]
    if not rows:
        raise ValueError(f"request file is empty: {path}")
    ids = [row["record_id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError(f"request file contains duplicate record IDs: {path}")
    records = [
        JudgeRecord(
            record_id=row["record_id"],
            source_problem_id=row["source_problem_id"],
            mode=JudgmentMode(row["mode"]),
            prompt=row["prompt"],
            rubric=[
                RubricCriterion(
                    criterion_id="gleif-closed-set-classification",
                    description="The single option that matches the frozen GLEIF source field.",
                    weight=1.0,
                    aggregation_rule="single_label",
                )
            ],
            candidate_a=row["candidate_a"],
            gold=GoldLabel(
                label="unscored",
                provenance=GoldProvenance.DETERMINISTIC_VERIFIER,
                evidence={"redacted": True},
                verifier_id="gleif-registry-classification-v1",
            ),
            split=Split.TEST,
        )
        for row in rows
    ]
    return rows, records


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
    request_path = Path(args.requests)
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

    request_rows, records = _load_requests(request_path, args.limit)
    labels = request_rows[0]["legal_labels"]
    criteria = request_rows[0]["criteria"]
    if any(row["legal_labels"] != labels or row["criteria"] != criteria for row in request_rows):
        raise ValueError("request file mixes more than one label set")
    expected = {record.record_id for record in records}
    if not set(existing).issubset(expected):
        raise ValueError("resume checkpoint contains an out-of-pool record ID")

    environment = {**_load_dotenv(Path(args.env_file) if args.env_file else None), **os.environ}
    api_key = environment.get("OPENROUTER_API_KEY")
    attempts_path = output / "attempts.json"
    attempts: dict[str, int] = {}
    if args.resume and attempts_path.is_file():
        attempts = json.loads(attempts_path.read_text(encoding="utf-8"))
    # A non-OK status is a provider fault, not a label; a resumed run re-attempts
    # it until the declared recovery budget is spent, then leaves it terminal.
    pending = [
        record
        for record in records
        if (
            record.record_id not in existing
            or existing[record.record_id].execution_status not in _TERMINAL_OK
        )
        and attempts.get(record.record_id, 0) < args.max_attempts
    ]
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
                label_set=labels,
                criteria=criteria,
            )[0]
        except Exception as exc:  # noqa: BLE001 - preserve one provider fault per record
            return _prediction_error(record, args.model, type(exc).__name__)

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(evaluate, record): record.record_id for record in pending}
        for future in as_completed(futures):
            prediction = future.result()
            existing[prediction.record_id] = prediction
    for record in pending:
        attempts[record.record_id] = attempts.get(record.record_id, 0) + 1

    if set(existing) != expected:
        raise RuntimeError("Jev run did not produce one status per selected request")
    ordered = [existing[record.record_id] for record in records]
    # Rewrite the whole checkpoint atomically so a retry replaces the prior fault
    # rather than appending a duplicate row for the same record ID.
    scratch = prediction_path.with_suffix(".jsonl.tmp")
    with scratch.open("w", encoding="utf-8") as handle:
        for prediction in ordered:
            handle.write(prediction.model_dump_json() + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(scratch, prediction_path)
    attempts_path.write_text(
        json.dumps(attempts, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    statuses = dict(
        sorted(Counter(prediction.execution_status.value for prediction in ordered).items())
    )
    pool_manifest = json.loads((EXPERIMENT_DIR / "pool-manifest.json").read_text(encoding="utf-8"))
    results = {
        "experiment_id": args.experiment_id,
        "run_id": output.name,
        "family": args.family,
        "provider": "openrouter",
        "requested_model": args.model,
        "route": "POST https://openrouter.ai/api/alpha/decisions",
        "partition": args.partition,
        "record_count": len(records),
        "workers": args.workers,
        "max_attempts": args.max_attempts,
        "attempted_this_pass": len(pending),
        "attempts_histogram": dict(
            sorted(Counter(str(count) for count in attempts.values()).items())
        ),
        "exhausted_budget_count": sum(
            1
            for record in records
            if existing[record.record_id].execution_status not in _TERMINAL_OK
            and attempts.get(record.record_id, 0) >= args.max_attempts
        ),
        "legal_labels": labels,
        "status_counts": statuses,
        "resolved_count": sum(
            prediction.execution_status is ExecutionStatus.OK for prediction in ordered
        ),
        "elapsed_seconds": time.perf_counter() - started,
        "source_pool": {
            "records_fingerprint": pool_manifest["records_fingerprint"],
            "blind_record_ids_fingerprint": pool_manifest["blind_record_ids_fingerprint"],
            "typed_question_spec_fingerprint": pool_manifest["typed_question_spec_fingerprint"],
            "label_sets_fingerprint": pool_manifest["label_sets_fingerprint"],
        },
        "requests_sha256": hashlib.sha256(request_path.read_bytes()).hexdigest(),
        "gold_not_read_by_runner": True,
        "created_at_utc": datetime.now(UTC).isoformat(),
    }
    (output / "results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "report.md").write_text(
        "\n".join(
            [
                f"# {args.experiment_id} — {output.name}",
                "",
                (
                    f"Family: `{args.family}`; partition: `{args.partition}`; "
                    f"records: `{len(records)}`; workers: `{args.workers}`."
                ),
                f"Label set: `{labels}`.",
                f"Status counts: `{statuses}`.",
                "",
                (
                    "The runner never reads a gold label. Provider failures and rate limits "
                    "remain execution statuses and are never counted as labels."
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    checksums = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "checksums.sha256":
            checksums.append(
                f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(output).as_posix()}"
            )
    (output / "checksums.sha256").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--family",
        required=True,
        choices=sorted(p.name[:-6] for p in (EXPERIMENT_DIR / "requests").glob("*.jsonl")),
    )
    parser.add_argument("--requests", type=Path)
    parser.add_argument("--experiment-id", default=EXPERIMENT_ID)
    parser.add_argument("--partition", default="blind_holdout")
    parser.add_argument("--model", default=OPENROUTER_PINNED_MODEL)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.limit < 0 or args.workers <= 0 or args.max_attempts <= 0:
        raise SystemExit(
            "--limit must be non-negative; --workers and --max-attempts must be positive"
        )
    if args.requests is None:
        args.requests = EXPERIMENT_DIR / "requests" / f"{args.family}.jsonl"
    print(json.dumps(_run(args), sort_keys=True))


if __name__ == "__main__":
    main()
