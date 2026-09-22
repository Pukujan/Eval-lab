"""Run the frozen matched multi-subscription bakeoff through OpenRouter."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from collections import Counter
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import httpx

from eval_lab.escalation.providers import normalize_typed_response
from eval_lab.escalation.spec import build_decision_spec
from eval_lab.reporting import build_report
from eval_lab.schema import ExecutionStatus, JudgePrediction, JudgeRecord

EXPERIMENT_ID = "EXP-20260920-011-openrouter-multi-subscription-bakeoff"
BENCHMARK_FINGERPRINT = "18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
PROTOCOL = "eval-lab-system-one-v1"
MODELS = {
    "grok": "x-ai/grok-4.6",
    "luna": "openai/gpt-5.6-luna",
    "sol": "openai/gpt-5.6-sol",
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
        if row["partition"] != "final_evaluation":
            continue
        record = JudgeRecord.model_validate(row["record"])
        records.append(record)
        domains[record.record_id] = str(row["domain"])
        if len(records) == limit:
            break
    if len(records) != limit:
        raise ValueError(f"final-evaluation pool contains only {len(records)} records; need {limit}")
    if len({record.record_id for record in records}) != len(records):
        raise ValueError("final-evaluation record IDs are not unique")
    return records, domains


def _payload(record: JudgeRecord, model: str) -> dict[str, Any]:
    spec = build_decision_spec(record)
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return a JSON object with a legal label."},
            {"role": "user", "content": json.dumps(spec.provider_payload(), sort_keys=True)},
        ],
        "temperature": 0,
        "max_tokens": 128,
        "stream": True,
    }


def _stream_content(response: httpx.Response) -> tuple[str, str | None]:
    chunks: list[str] = []
    returned_model: str | None = None
    for raw_line in response.iter_lines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("data:"):
            line = line[5:].strip()
        if line == "[DONE]":
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, Mapping):
            continue
        if event.get("model") is not None:
            returned_model = str(event["model"])
        choices = event.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], Mapping):
            continue
        choice = choices[0]
        part = choice.get("delta") or choice.get("message") or {}
        if isinstance(part, Mapping) and isinstance(part.get("content"), str):
            chunks.append(str(part["content"]))
    return "".join(chunks), returned_model


def _error(
    record: JudgeRecord,
    *,
    arm_id: str,
    model: str,
    status: ExecutionStatus,
    started: float,
    kind: str,
    **details: Any,
) -> JudgePrediction:
    return JudgePrediction(
        record_id=record.record_id,
        judge_id=model,
        protocol_version=PROTOCOL,
        execution_status=status,
        latency_ms=(time.perf_counter() - started) * 1000.0,
        provider_metadata={
            "provider": "openrouter",
            "arm_id": arm_id,
            "requested_model": model,
            "typed_spec_id": "eval-lab-system-one",
            "typed_spec_version": "0.1.0",
            "streaming": True,
            "granularity": "one_record_per_request",
        },
        error={"kind": kind, **details},
    )


def _run_one(
    record: JudgeRecord,
    *,
    arm_id: str,
    model: str,
    client: httpx.Client,
    api_key: str,
    timeout: float,
) -> JudgePrediction:
    started = time.perf_counter()
    try:
        with client.stream(
            "POST",
            ENDPOINT,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/Pukujan/Eval-lab",
                "X-Title": "Eval Lab TASK-0010",
            },
            json=_payload(record, model),
            timeout=timeout,
        ) as response:
            if response.status_code == 429:
                return _error(
                    record,
                    arm_id=arm_id,
                    model=model,
                    status=ExecutionStatus.RATE_LIMITED,
                    started=started,
                    kind="rate_limited",
                )
            if response.status_code >= 400:
                return _error(
                    record,
                    arm_id=arm_id,
                    model=model,
                    status=ExecutionStatus.PROVIDER_ERROR,
                    started=started,
                    kind="http_status",
                    status_code=response.status_code,
                )
            content, returned_model = _stream_content(response)
    except httpx.TimeoutException:
        return _error(
            record,
            arm_id=arm_id,
            model=model,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            kind="timeout",
        )
    except httpx.HTTPError as exc:
        return _error(
            record,
            arm_id=arm_id,
            model=model,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            kind="transport_error",
            error_type=type(exc).__name__,
        )
    if returned_model is not None and returned_model != model:
        return _error(
            record,
            arm_id=arm_id,
            model=model,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            kind="model_identity_mismatch",
            returned_model=returned_model,
        )
    try:
        prediction = normalize_typed_response(
            {"model": returned_model or model, "choices": [{"message": {"content": content}}]},
            record,
            provider="openrouter",
            model=model,
            latency_ms=(time.perf_counter() - started) * 1000.0,
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        return _error(
            record,
            arm_id=arm_id,
            model=model,
            status=ExecutionStatus.PARSE_ERROR,
            started=started,
            kind="label_not_found",
        )
    prediction.provider_metadata.update(
        {
            "arm_id": arm_id,
            "requested_model": model,
            "returned_model": returned_model or model,
            "streaming": True,
            "granularity": "one_record_per_request",
        }
    )
    return prediction


def _run_arm(
    records: list[JudgeRecord],
    *,
    arm_id: str,
    model: str,
    api_key: str,
    timeout: float,
    workers: int,
) -> list[JudgePrediction]:
    def evaluate(record: JudgeRecord) -> JudgePrediction:
        with httpx.Client() as client:
            return _run_one(
                record,
                arm_id=arm_id,
                model=model,
                client=client,
                api_key=api_key,
                timeout=timeout,
            )

    if workers <= 1:
        return [evaluate(record) for record in records]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(evaluate, records))


def _write_jsonl(path: Path, predictions: list[JudgePrediction]) -> None:
    path.write_text(
        "".join(prediction.model_dump_json() + "\n" for prediction in predictions), encoding="utf-8"
    )


def _checksums(root: Path) -> None:
    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "checksums.sha256":
            continue
        entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}")
    (root / "checksums.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")


def _differential(records: list[JudgeRecord], predictions: dict[str, list[JudgePrediction]]) -> dict[str, Any]:
    by_arm = {arm: {item.record_id: item for item in values} for arm, values in predictions.items()}
    arms = sorted(predictions)
    pairs: dict[str, dict[str, int]] = {}
    for left_index, left in enumerate(arms):
        for right in arms[left_index + 1 :]:
            comparable = 0
            agreement = 0
            for record in records:
                left_item = by_arm[left][record.record_id]
                right_item = by_arm[right][record.record_id]
                if left_item.execution_status is ExecutionStatus.OK and right_item.execution_status is ExecutionStatus.OK:
                    comparable += 1
                    agreement += int(left_item.label == right_item.label)
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
    environment = {**_load_dotenv(Path(args.env_file) if args.env_file else None), **os.environ}
    api_key = environment.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is unavailable")
    records, domains = _load_records(Path(args.benchmark), args.limit)
    selected = tuple(args.models.split(",")) if args.models else tuple(MODELS)
    unknown = sorted(set(selected) - set(MODELS))
    if unknown:
        raise ValueError(f"unknown arm(s): {unknown}")
    predictions: dict[str, list[JudgePrediction]] = {}
    reports: dict[str, Any] = {}
    for arm_id in selected:
        arm_predictions = _run_arm(
            records,
            arm_id=arm_id,
            model=MODELS[arm_id],
            api_key=api_key,
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
    results = {
        "experiment_id": EXPERIMENT_ID,
        "status": "completed"
        if all(report["status_counts"].get("ok", 0) == len(records) for report in reports.values())
        else "completed_with_provider_statuses",
        "benchmark_fingerprint": BENCHMARK_FINGERPRINT,
        "counts": {
            "provider_evaluation": len(records),
            "arms_attempted": len(selected),
            "record_ids_unique": len({record.record_id for record in records}) == len(records),
        },
        "streaming": True,
        "granularity": "one_record_per_request",
        "endpoint": ENDPOINT,
        "arms": reports,
        "differential": _differential(records, predictions),
    }
    (output / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "provider-status.json").write_text(
        json.dumps(
            {"endpoint": ENDPOINT, "arms": {arm: report["status_counts"] for arm, report in reports.items()}},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (output / "differential.json").write_text(
        json.dumps(results["differential"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "report.md").write_text(
        "# EXP-20260920-011 OpenRouter bakeoff\n\n"
        f"Frozen provider records: {len(records)}\n\n"
        + "\n".join(
            f"- `{arm}` `{MODELS[arm]}`: `{report['status_counts']}`"
            for arm, report in reports.items()
        )
        + "\n",
        encoding="utf-8",
    )
    _checksums(output)
    return {"experiment_id": EXPERIMENT_ID, "status": results["status"], "arms": {arm: report["status_counts"] for arm, report in reports.items()}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=Path("benchmark/eval-lab-select-v0.1.0"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--models")
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args), sort_keys=True))


if __name__ == "__main__":
    main()
