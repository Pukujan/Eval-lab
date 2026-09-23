"""Leakage and release checks for the frozen selective benchmark."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from eval_lab.datasets.selective import partition_records
from eval_lab.schema import JudgeRecord

ROOT = Path("benchmark/eval-lab-select-v0.1.0")


def _rows() -> list[dict]:
    return [json.loads(line) for line in (ROOT / "records.jsonl").read_text(encoding="utf-8").splitlines()]


def test_frozen_partitions_meet_size_and_source_leakage_contract() -> None:
    rows = _rows()
    threshold = [row for row in rows if row["partition"] == "threshold_selection"]
    final = [row for row in rows if row["partition"] == "final_evaluation"]
    assert len(threshold) >= 200
    assert len(final) >= 500
    assert {row["record"]["source_problem_id"] for row in threshold}.isdisjoint(
        {row["record"]["source_problem_id"] for row in final}
    )
    assert len({row["record"]["record_id"] for row in rows}) == len(rows)


def test_benchmark_records_round_trip_and_checksums_are_current() -> None:
    rows = _rows()
    records = [JudgeRecord.model_validate(row["record"]) for row in rows]
    partitions = partition_records(records)
    assert len(partitions["threshold_selection"]) == 2863
    assert len(partitions["final_evaluation"]) == 2356
    for line in (ROOT / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest


def test_benchmark_fingerprint_is_explicit_and_hex() -> None:
    payload = json.loads((ROOT / "fingerprint.json").read_text(encoding="utf-8"))
    fingerprint = payload["fingerprint"]
    assert len(fingerprint) == 64
    int(fingerprint, 16)

