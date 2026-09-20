"""Merge successful targeted Qwen streaming retries into a new append-only run."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from eval_lab.reporting import build_report
from eval_lab.schema import ExecutionStatus, JudgePrediction

try:
    from scripts.run_qwen_streaming_retry import BENCHMARK_FINGERPRINT, MODEL, _load_records
except ModuleNotFoundError:
    from run_qwen_streaming_retry import BENCHMARK_FINGERPRINT, MODEL, _load_records


def _load_predictions(path: Path) -> list[JudgePrediction]:
    return [
        JudgePrediction.model_validate_json(line)
        for line in (path / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _checksums(root: Path) -> None:
    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "checksums.sha256":
            continue
        entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}")
    (root / "checksums.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")


def merge(source: Path, retry: Path, output: Path, benchmark: Path) -> dict[str, Any]:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite existing merged output: {output}")
    source_results = json.loads((source / "results.json").read_text(encoding="utf-8"))
    retry_results = json.loads((retry / "results.json").read_text(encoding="utf-8"))
    if source_results["benchmark_fingerprint"] != BENCHMARK_FINGERPRINT:
        raise ValueError("source fingerprint mismatch")
    if retry_results["benchmark_fingerprint"] != BENCHMARK_FINGERPRINT:
        raise ValueError("retry fingerprint mismatch")
    source_predictions = _load_predictions(source)
    retry_predictions = _load_predictions(retry)
    if any(prediction.judge_id != MODEL for prediction in source_predictions + retry_predictions):
        raise ValueError("Qwen model identity changed")
    source_by_id = {prediction.record_id: prediction for prediction in source_predictions}
    retry_by_id = {prediction.record_id: prediction for prediction in retry_predictions}
    if len(source_by_id) != len(source_predictions) or len(retry_by_id) != len(retry_predictions):
        raise ValueError("duplicate prediction record IDs")
    if any(source_by_id[record_id].execution_status is not ExecutionStatus.PARSE_ERROR for record_id in retry_by_id):
        raise ValueError("retry contains a record that was not a source parse error")
    merged = [retry_by_id.get(prediction.record_id, prediction) for prediction in source_predictions]
    if any(prediction.execution_status is not ExecutionStatus.OK for prediction in merged):
        raise ValueError("merged run still contains unresolved predictions")
    records, domains = _load_records(benchmark, len(merged))
    if [record.record_id for record in records] != [prediction.record_id for prediction in merged]:
        raise ValueError("merged IDs do not match the frozen benchmark prefix")
    output.mkdir(parents=True, exist_ok=True)
    (output / "predictions.jsonl").write_text(
        "".join(prediction.model_dump_json() + "\n" for prediction in merged), encoding="utf-8"
    )
    counts = dict(Counter(prediction.execution_status.value for prediction in merged))
    results = {
        "experiment_id": "EXP-20260920-009-selective-escalation",
        "retry_id": output.name,
        "benchmark_fingerprint": BENCHMARK_FINGERPRINT,
        "model": MODEL,
        "limit": len(merged),
        "streaming": True,
        "granularity": "one_record_per_request",
        "status_counts": counts,
        "report": build_report(records, merged, domain_by_record_id=domains),
        "merge": {"source": source.name, "retry": retry.name, "replaced_count": len(retry_by_id)},
    }
    (output / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "provider-status.json").write_text(
        json.dumps({"model": MODEL, "status_counts": counts, "replaced_count": len(retry_by_id)}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "merge-manifest.json").write_text(
        json.dumps(
            {"source": source.name, "retry": retry.name, "replaced_record_ids": sorted(retry_by_id)},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    _checksums(output)
    return {"retry_id": output.name, "status_counts": counts, "replaced_count": len(retry_by_id)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--retry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, default=Path("benchmark/eval-lab-select-v0.1.0"))
    args = parser.parse_args()
    print(json.dumps(merge(args.source, args.retry, args.output, args.benchmark), sort_keys=True))


if __name__ == "__main__":
    main()
