"""Run the preregistered multi-subscription bakeoff on the frozen benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import time
from collections import Counter
from collections.abc import Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from eval_lab.escalation.spec import build_decision_spec
from eval_lab.reporting import build_report
from eval_lab.schema import (
    ExecutionStatus,
    JudgePrediction,
    JudgeRecord,
    JudgmentMode,
    PairwiseLabel,
)

BENCHMARK = Path("benchmark/eval-lab-select-v0.1.0")
EXPERIMENT = Path("experiments/EXP-20260920-010-multi-subscription-bakeoff")
PROTOCOL = "eval-lab-system-one-v0.1.0"
MODELS = {
    "grok": "opencode/grok-4.6",
    "luna": "opencode/gpt-5.6-luna",
    "sol": "opencode/gpt-5.6-sol",
}
DEFERRED = {
    "qwen_flash": {
        "provider": "yolo-auto",
        "model": "qwen3.8-flash",
        "status": "deferred_provider_blocked",
        "reason": "TASK-0010 YOLO-Auto provider block",
    },
    "qwen_local_1_7b": {
        "provider": "local",
        "model": "Qwen3-1.7B",
        "status": "deferred_weights_unavailable",
        "reason": "no local weights in the standard Hugging Face cache",
    },
    "qwen_local_4b": {
        "provider": "local",
        "model": "Qwen3-4B",
        "status": "deferred_weights_unavailable",
        "reason": "no local weights in the standard Hugging Face cache",
    },
}


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


def _load_records(benchmark: Path, limit: int) -> tuple[list[JudgeRecord], dict[str, str]]:
    records: list[JudgeRecord] = []
    domains: dict[str, str] = {}
    for raw in (benchmark / "records.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(raw)
        if row.get("partition") != "final_evaluation":
            continue
        record = JudgeRecord.model_validate(row["record"])
        records.append(record)
        domains[record.record_id] = str(row["domain"])
        if len(records) == limit:
            break
    if not records:
        raise ValueError("the final-evaluation provider pool is empty")
    if len({record.record_id for record in records}) != len(records):
        raise ValueError("provider pool contains duplicate record IDs")
    return records, domains


def _nested_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _nested_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _nested_mappings(child)


def _json_fragments(text: str) -> Iterable[Mapping[str, Any]]:
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, Mapping):
            yield value


def _legal_labels(record: JudgeRecord) -> set[str]:
    if record.mode is JudgmentMode.SINGLE:
        return {"pass", "fail"}
    return {item.value for item in PairwiseLabel}


def parse_label(text: str, record: JudgeRecord) -> str | None:
    """Extract one legal label from an OpenCode JSON/event stream."""

    legal = _legal_labels(record)
    for fragment in _json_fragments(text):
        for mapping in _nested_mappings(fragment):
            for key in ("label", "verdict", "prediction", "choice", "class", "value"):
                value = mapping.get(key)
                if isinstance(value, Mapping):
                    value = next(
                        (value.get(candidate) for candidate in ("label", "choice", "value") if candidate in value),
                        None,
                    )
                if value is None:
                    continue
                candidate = str(value).strip()
                normalized = candidate.upper() if record.mode is JudgmentMode.PAIRWISE else candidate.lower()
                if normalized in legal:
                    return normalized
    normalized = text.upper() if record.mode is JudgmentMode.PAIRWISE else text.lower()
    token_pattern = r"\b(?:A|B|TIE)\b" if record.mode is JudgmentMode.PAIRWISE else r"\b(?:PASS|FAIL)\b"
    tokens = re.findall(token_pattern, normalized)
    for token in reversed(tokens):
        candidate = token if record.mode is JudgmentMode.PAIRWISE else token.lower()
        if candidate in legal:
            return candidate
    return None


def _surfaced_models(text: str) -> list[str]:
    models: set[str] = set()
    for fragment in _json_fragments(text):
        for mapping in _nested_mappings(fragment):
            for key in ("model", "model_id", "modelID", "modelId"):
                value = mapping.get(key)
                if isinstance(value, str) and value:
                    models.add(value)
    return sorted(models)


def _prompt(record: JudgeRecord) -> str:
    decision = build_decision_spec(record)
    payload = {"record_id": decision.record_id, **decision.provider_payload()}
    labels = ", ".join(decision.legal_labels)
    return (
        "You are a strictly typed objective evaluation judge. "
        f"Return exactly one JSON object with label set to one of [{labels}]. "
        "Do not include explanation, markdown, or additional keys.\n\n"
        + json.dumps(payload, sort_keys=True)
    )


def _prediction(
    record: JudgeRecord,
    *,
    arm_id: str,
    model: str,
    status: ExecutionStatus,
    started: float,
    label: str | None = None,
    error: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> JudgePrediction:
    return JudgePrediction(
        record_id=record.record_id,
        judge_id=model,
        protocol_version=PROTOCOL,
        label=label,
        execution_status=status,
        latency_ms=(time.perf_counter() - started) * 1000.0,
        provider_metadata={
            "provider": "opencode",
            "arm_id": arm_id,
            "requested_model": model,
            "typed_spec_id": "eval-lab-system-one",
            "typed_spec_version": "0.1.0",
            "cli": "opencode",
            **(metadata or {}),
        },
        error=error,
    )


def _run_one(
    record: JudgeRecord,
    *,
    arm_id: str,
    model: str,
    environment: dict[str, str],
    timeout: float,
) -> JudgePrediction:
    started = time.perf_counter()
    executable = environment.get("OPENCODE_EXE") or shutil.which("opencode") or "opencode"
    command = [
        executable,
        "run",
        "--model",
        model,
        "--format",
        "json",
        "--log-level",
        "ERROR",
        "--dir",
        str(Path.cwd()),
        _prompt(record),
    ]
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, **environment},
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
    except OSError as exc:
        return _prediction(
            record,
            arm_id=arm_id,
            model=model,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "process_error", "type": type(exc).__name__},
        )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            text=True,
            check=False,
        )
        return _prediction(
            record,
            arm_id=arm_id,
            model=model,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "timeout"},
        )
    output = (stdout or "") + "\n" + (stderr or "")
    if process.returncode != 0:
        return _prediction(
            record,
            arm_id=arm_id,
            model=model,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "process_exit", "returncode": process.returncode},
        )
    label = parse_label(output, record)
    models = _surfaced_models(output)
    if label is None:
        return _prediction(
            record,
            arm_id=arm_id,
            model=model,
            status=ExecutionStatus.PARSE_ERROR,
            started=started,
            error={"kind": "label_not_found"},
            metadata={"surfaced_model_ids": models},
        )
    return _prediction(
        record,
        arm_id=arm_id,
        model=model,
        status=ExecutionStatus.OK,
        started=started,
        label=label,
        metadata={"surfaced_model_ids": models},
    )


def _run_arm(
    records: list[JudgeRecord],
    *,
    arm_id: str,
    model: str,
    environment: dict[str, str],
    timeout: float,
    workers: int,
) -> list[JudgePrediction]:
    if workers <= 1:
        return [
            _run_one(record, arm_id=arm_id, model=model, environment=environment, timeout=timeout)
            for record in records
        ]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                _run_one,
                record,
                arm_id=arm_id,
                model=model,
                environment=environment,
                timeout=timeout,
            )
            for record in records
        ]
        return [future.result() for future in futures]


def _write_jsonl(path: Path, predictions: list[JudgePrediction]) -> None:
    path.write_text(
        "".join(prediction.model_dump_json() + "\n" for prediction in predictions),
        encoding="utf-8",
    )


def _checksums(root: Path) -> None:
    entries: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "checksums.sha256":
            continue
        relative = path.relative_to(root).as_posix()
        entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}")
    (root / "checksums.sha256").write_bytes(("\n".join(entries) + "\n").encode("utf-8"))


def _differential(
    records: list[JudgeRecord], predictions: dict[str, list[JudgePrediction]]
) -> dict[str, Any]:
    by_arm = {
        arm: {prediction.record_id: prediction for prediction in values}
        for arm, values in predictions.items()
    }
    pairs: dict[str, dict[str, int]] = {}
    arms = sorted(predictions)
    for left_index, left in enumerate(arms):
        for right in arms[left_index + 1 :]:
            comparable = 0
            agreement = 0
            for record in records:
                left_prediction = by_arm[left][record.record_id]
                right_prediction = by_arm[right][record.record_id]
                if (
                    left_prediction.execution_status is ExecutionStatus.OK
                    and right_prediction.execution_status is ExecutionStatus.OK
                ):
                    comparable += 1
                    agreement += int(left_prediction.label == right_prediction.label)
            pairs[f"{left}__vs__{right}"] = {
                "comparable_count": comparable,
                "agreement_count": agreement,
            }
    return {"arms": arms, "pairs": pairs}


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.output)
    if (output / "results.json").exists() or (output / "predictions").exists():
        raise FileExistsError("refusing to overwrite an existing bakeoff result")
    output.mkdir(parents=True, exist_ok=True)
    prediction_dir = output / "predictions"
    prediction_dir.mkdir()
    environment = _load_dotenv(Path(args.env_file) if args.env_file else None)
    records, domains = _load_records(Path(args.benchmark), args.limit)
    selected = tuple(args.models.split(",")) if args.models else tuple(MODELS)
    unknown = sorted(set(selected) - set(MODELS))
    if unknown:
        raise ValueError(f"unknown subscription arm(s): {unknown}")
    predictions: dict[str, list[JudgePrediction]] = {}
    reports: dict[str, Any] = {}
    for arm_id in selected:
        arm_predictions = _run_arm(
            records,
            arm_id=arm_id,
            model=MODELS[arm_id],
            environment=environment,
            timeout=args.timeout,
            workers=args.workers,
        )
        predictions[arm_id] = arm_predictions
        _write_jsonl(prediction_dir / f"{arm_id}.jsonl", arm_predictions)
        reports[arm_id] = {
            "model": MODELS[arm_id],
            "status_counts": dict(Counter(item.execution_status.value for item in arm_predictions)),
            "report": build_report(records, arm_predictions, domain_by_record_id=domains),
        }
    differential = _differential(records, predictions)
    results = {
        "experiment_id": "EXP-20260920-010-multi-subscription-bakeoff",
        "status": "completed"
        if all(report["status_counts"].get("ok", 0) == len(records) for report in reports.values())
        else "completed_with_provider_statuses",
        "benchmark_fingerprint": "18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5",
        "counts": {
            "provider_evaluation": len(records),
            "arms_attempted": len(selected),
            "record_ids_unique": len({record.record_id for record in records}) == len(records),
        },
        "pool_rule": "deterministic first 500 final-evaluation records",
        "student": {"source_task": "TASK-0009", "selected_arm": "D", "retrained": False},
        "typed_system_one": {"spec_id": "eval-lab-system-one", "spec_version": "0.1.0"},
        "arms": reports,
        "differential": differential,
        "deferred_arms": DEFERRED,
        "environment": {"platform": platform.platform(), "python": platform.python_version()},
    }
    (output / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "provider-status.json").write_text(
        json.dumps({"deferred_arms": DEFERRED}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report_lines = [
        "# EXP-20260920-010 — Multi-subscription judge bakeoff",
        "",
        f"Benchmark fingerprint: `{results['benchmark_fingerprint']}`.",
        f"Matched final-evaluation records: {len(records)}.",
        "",
        "| Arm | Model | OK | Provider error | Parse error | Other |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for arm_id, report in reports.items():
        counts = report["status_counts"]
        other = sum(value for key, value in counts.items() if key not in {"ok", "provider_error", "parse_error"})
        report_lines.append(
            f"| {arm_id} | `{report['model']}` | {counts.get('ok', 0)} | "
            f"{counts.get('provider_error', 0)} | {counts.get('parse_error', 0)} | {other} |"
        )
    report_lines.extend(
        [
            "",
            "Provider failures remain unresolved and receive no local fallback label.",
            "Deferred Qwen and local-weight arms are recorded in `provider-status.json`.",
        ]
    )
    (output / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    _checksums(output)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=BENCHMARK)
    parser.add_argument("--output", type=Path, default=EXPERIMENT)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--models", help="comma-separated arm IDs; default: grok,luna,sol")
    args = parser.parse_args()
    if args.limit <= 0 or args.workers <= 0:
        raise SystemExit("--limit and --workers must be positive")
    result = run(args)
    print(json.dumps({"experiment_id": result["experiment_id"], "status": result["status"], "arms": result["arms"]}, sort_keys=True))


if __name__ == "__main__":
    main()
