"""Run one frozen matched arm set for EXP-20260921-015."""

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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from eval_lab.escalation.providers import run_yolo_qwen
from eval_lab.escalation.spec import build_decision_spec
from eval_lab.reporting import build_report
from eval_lab.schema import (
    ExecutionStatus,
    JudgePrediction,
    JudgeRecord,
    JudgmentMode,
    PairwiseLabel,
)

EXPERIMENT_ID = "EXP-20260921-015-grok-luna-qwen-bakeoff"
PROTOCOL = "eval-lab-system-one-v1"
POOL = Path("experiments") / EXPERIMENT_ID
ARMS = {
    "grok": {
        "provider": "xai-grok-build-cli",
        "requested_model": "grok-4.6",
        "route": "direct_grok_build_cli_subscription",
    },
    "luna": {
        "provider": "codex",
        "requested_model": "gpt-5.6-luna",
        "route": "direct_codex_chatgpt_subscription",
    },
    "qwen_flash": {
        "provider": "yolo-auto",
        "requested_model": "qwen3.8-flash",
        "route": "yolo_auto_openai_compatible",
    },
    "sol": {
        "provider": "codex",
        "requested_model": "gpt-5.6-sol",
        "route": "direct_codex_chatgpt_subscription",
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


def _load_pool(
    pool: Path,
    partition: str,
    limit: int,
    record_ids_file: Path | None,
) -> tuple[list[dict[str, Any]], list[JudgeRecord], dict[str, str]]:
    rows = [
        json.loads(line)
        for line in (pool / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    requested_ids = None
    if record_ids_file is not None:
        requested_ids = {
            line.strip()
            for line in record_ids_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        if not requested_ids:
            raise ValueError("record ID file is empty")
    selected = [
        row
        for row in rows
        if (partition == "all" or row["partition"] == partition)
        and (requested_ids is None or row["record"]["record_id"] in requested_ids)
    ]
    if requested_ids is None and limit:
        selected = selected[:limit]
    expected = len(requested_ids) if requested_ids is not None else len(selected)
    if not selected or len(selected) != expected:
        raise ValueError(f"selected pool has {len(selected)} records; expected {expected}")
    records = [JudgeRecord.model_validate(row["record"]) for row in selected]
    if len({record.record_id for record in records}) != len(records):
        raise ValueError("selected pool contains duplicate record IDs")
    domains = {record.record_id: str(row.get("dataset", "unknown")) for row, record in zip(selected, records, strict=True)}
    if requested_ids is not None and {record.record_id for record in records} != requested_ids:
        raise ValueError("record ID file contains an ID outside the selected partition")
    return selected, records, domains


def _nested_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _nested_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _nested_mappings(child)
    elif isinstance(value, str) and value.strip().startswith(("{", "[")):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return
        if isinstance(decoded, (Mapping, list)):
            yield from _nested_mappings(decoded)


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
    """Extract one legal label from a direct CLI response/event stream."""

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
            for key in ("model", "model_id", "modelID", "modelId", "resolved_model"):
                value = mapping.get(key)
                if isinstance(value, str) and value:
                    models.add(value)
            model_usage = mapping.get("modelUsage")
            if isinstance(model_usage, Mapping):
                models.update(str(key) for key in model_usage if str(key))
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


def _grok_json_schema(record: JudgeRecord) -> str:
    return json.dumps(
        {
            "type": "object",
            "properties": {"label": {"type": "string", "enum": sorted(_legal_labels(record))}},
            "required": ["label"],
            "additionalProperties": False,
        },
        separators=(",", ":"),
    )


def _prediction(
    record: JudgeRecord,
    *,
    arm_id: str,
    provider: str,
    model: str,
    route: str,
    status: ExecutionStatus,
    started: float,
    label: str | None = None,
    error: dict[str, Any] | None = None,
    surfaced_model_ids: list[str] | None = None,
) -> JudgePrediction:
    return JudgePrediction(
        record_id=record.record_id,
        judge_id=model,
        protocol_version=PROTOCOL,
        label=label,
        execution_status=status,
        latency_ms=(time.perf_counter() - started) * 1000.0,
        provider_metadata={
            "provider": provider,
            "arm_id": arm_id,
            "requested_model": model,
            "route": route,
            "typed_spec_id": "eval-lab-system-one",
            "typed_spec_version": "0.1.0",
            "surfaced_model_ids": surfaced_model_ids or [],
        },
        error=error,
    )


def _run_codex_one(
    record: JudgeRecord,
    *,
    arm_id: str,
    model: str,
    route: str,
    environment: dict[str, str],
    timeout: float,
) -> JudgePrediction:
    """Run Codex CLI directly with the authenticated ChatGPT subscription."""

    started = time.perf_counter()
    executable = environment.get("CODEX_EXE") or shutil.which("codex") or "codex"
    command = [
        executable,
        "exec",
        "--model",
        model,
        "--cd",
        str(Path.cwd()),
        "--sandbox",
        "read-only",
        "--ephemeral",
        "--json",
        "-",
    ]
    try:
        process = subprocess.run(
            command,
            input=_prompt(record),
            capture_output=True,
            text=True,
            env=environment,
            timeout=timeout,
            check=False,
        )
    except OSError as exc:
        return _prediction(
            record,
            arm_id=arm_id,
            provider="codex",
            model=model,
            route=route,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "process_error", "type": type(exc).__name__},
        )
    except subprocess.TimeoutExpired:
        return _prediction(
            record,
            arm_id=arm_id,
            provider="codex",
            model=model,
            route=route,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "timeout"},
        )
    output = (process.stdout or "") + "\n" + (process.stderr or "")
    surfaced: list[str] = []
    thread_id: str | None = None
    for line in (process.stdout or "").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started" and isinstance(event.get("thread_id"), str):
            thread_id = event["thread_id"]
    metadata = {"codex_cli": "codex", "thread_id": thread_id} if thread_id else {"codex_cli": "codex"}
    if process.returncode != 0:
        lower = output.lower()
        status = ExecutionStatus.RATE_LIMITED if "429" in lower or "rate limit" in lower else ExecutionStatus.PROVIDER_ERROR
        kind = "rate_limited" if status is ExecutionStatus.RATE_LIMITED else "process_exit"
        return _prediction(
            record,
            arm_id=arm_id,
            provider="codex",
            model=model,
            route=route,
            status=status,
            started=started,
            error={"kind": kind, "returncode": process.returncode},
            surfaced_model_ids=surfaced,
        )
    label = parse_label(output, record)
    if label is None:
        return _prediction(
            record,
            arm_id=arm_id,
            provider="codex",
            model=model,
            route=route,
            status=ExecutionStatus.PARSE_ERROR,
            started=started,
            error={"kind": "label_not_found"},
            surfaced_model_ids=surfaced,
        )
    prediction = _prediction(
        record,
        arm_id=arm_id,
        provider="codex",
        model=model,
        route=route,
        status=ExecutionStatus.OK,
        started=started,
        label=label,
        surfaced_model_ids=surfaced,
    )
    prediction.provider_metadata.update(metadata)
    return prediction


def _run_grok_build_one(
    record: JudgeRecord,
    *,
    arm_id: str,
    model: str,
    route: str,
    environment: dict[str, str],
    timeout: float,
) -> JudgePrediction:
    """Run the direct xAI Grok Build CLI through the subscription session."""

    started = time.perf_counter()
    executable = environment.get("GROK_EXE") or shutil.which("grok") or "grok"
    command = [
        executable,
        "--model",
        model,
        "--output-format",
        "json",
        "--json-schema",
        _grok_json_schema(record),
        "--max-turns",
        "1",
        "--disable-web-search",
        "--verbatim",
        "--no-subagents",
        "--no-plan",
        "--permission-mode",
        "dontAsk",
        f"--single={_prompt(record)}",
    ]
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
    except OSError as exc:
        return _prediction(
            record,
            arm_id=arm_id,
            provider="xai-grok-build-cli",
            model=model,
            route=route,
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
            provider="xai-grok-build-cli",
            model=model,
            route=route,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "timeout"},
        )
    output = (stdout or "") + "\n" + (stderr or "")
    surfaced = _surfaced_models(output)
    if process.returncode != 0:
        lower = output.lower()
        status = ExecutionStatus.RATE_LIMITED if "429" in lower or "rate limit" in lower else ExecutionStatus.PROVIDER_ERROR
        kind = "rate_limited" if status is ExecutionStatus.RATE_LIMITED else "process_exit"
        return _prediction(
            record,
            arm_id=arm_id,
            provider="xai-grok-build-cli",
            model=model,
            route=route,
            status=status,
            started=started,
            error={"kind": kind, "returncode": process.returncode},
            surfaced_model_ids=surfaced,
        )
    label = parse_label(output, record)
    if label is None:
        return _prediction(
            record,
            arm_id=arm_id,
            provider="xai-grok-build-cli",
            model=model,
            route=route,
            status=ExecutionStatus.PARSE_ERROR,
            started=started,
            error={"kind": "label_not_found"},
            surfaced_model_ids=surfaced,
        )
    return _prediction(
        record,
        arm_id=arm_id,
        provider="xai-grok-build-cli",
        model=model,
        route=route,
        status=ExecutionStatus.OK,
        started=started,
        label=label,
        surfaced_model_ids=surfaced,
    )


def _run_grok_build_arm(
    records: list[JudgeRecord],
    *,
    arm_id: str,
    model: str,
    route: str,
    environment: dict[str, str],
    timeout: float,
) -> list[JudgePrediction]:
    return [
        _run_grok_build_one(
            record,
            arm_id=arm_id,
            model=model,
            route=route,
            environment=environment,
            timeout=timeout,
        )
        for record in records
    ]


def _run_codex_arm(
    records: list[JudgeRecord],
    *,
    arm_id: str,
    model: str,
    route: str,
    environment: dict[str, str],
    timeout: float,
    workers: int,
) -> list[JudgePrediction]:
    def evaluate(record: JudgeRecord) -> JudgePrediction:
        return _run_codex_one(
            record,
            arm_id=arm_id,
            model=model,
            route=route,
            environment=environment,
            timeout=timeout,
        )

    if workers <= 1:
        return [evaluate(record) for record in records]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(evaluate, records))


def _run_qwen_arm(
    records: list[JudgeRecord],
    *,
    arm_id: str,
    model: str,
    route: str,
    environment: dict[str, str],
    timeout: float,
) -> list[JudgePrediction]:
    api_key = environment.get("YOLO_AUTO_API_KEY") or environment.get("YOLO_API_KEY") or environment.get("QWEN_API_KEY")
    base_url = (
        environment.get("YOLO_AUTO_BASE_URL")
        or environment.get("QWEN_API_URL")
        or "https://api.yolo-auto.com/v1"
    )
    predictions: list[JudgePrediction] = []
    with httpx.Client(timeout=timeout) as client:
        for record in records:
            started = time.perf_counter()
            try:
                prediction = run_yolo_qwen(
                    [record],
                    model=model,
                    api_key=api_key,
                    base_url=base_url,
                    client=client,
                    timeout=timeout,
                )[0]
            except (httpx.HTTPError, OSError, ValueError) as exc:
                prediction = _prediction(
                    record,
                    arm_id=arm_id,
                    provider="yolo-auto",
                    model=model,
                    route=route,
                    status=ExecutionStatus.PROVIDER_ERROR,
                    started=started,
                    error={"kind": "adapter_error", "type": type(exc).__name__},
                )
            prediction.provider_metadata.update(
                {
                    "arm_id": arm_id,
                    "requested_model": model,
                    "route": route,
                    "base_url": base_url,
                    "surfaced_model_ids": [
                        str(prediction.provider_metadata["resolved_model"])
                    ]
                    if prediction.provider_metadata.get("resolved_model")
                    else [],
                }
            )
            predictions.append(prediction)
    return predictions


def _wilson(successes: int, trials: int) -> dict[str, float] | None:
    if trials == 0:
        return None
    z = 1.959963984540054
    estimate = successes / trials
    denominator = 1 + z * z / trials
    center = (estimate + z * z / (2 * trials)) / denominator
    margin = z * (estimate * (1 - estimate) / trials + z * z / (4 * trials * trials)) ** 0.5 / denominator
    return {"lower": max(0.0, center - margin), "upper": min(1.0, center + margin)}


def _arm_summary(
    records: list[JudgeRecord],
    predictions: list[JudgePrediction],
    domains: dict[str, str],
    arm: dict[str, str],
) -> dict[str, Any]:
    resolved = [
        (record, prediction)
        for record, prediction in zip(records, predictions, strict=True)
        if prediction.execution_status is ExecutionStatus.OK and prediction.label is not None
    ]
    correct = sum(record.gold.label == prediction.label for record, prediction in resolved)
    surfaced = sorted(
        {
            surfaced
            for prediction in predictions
            for surfaced in prediction.provider_metadata.get("surfaced_model_ids", [])
        }
    )
    error_kinds = Counter(
        str((prediction.error or {}).get("kind") or (prediction.error or {}).get("type") or "unknown")
        for prediction in predictions
        if prediction.execution_status is not ExecutionStatus.OK
    )
    usage = [
        prediction.provider_metadata.get("usage")
        for prediction in predictions
        if isinstance(prediction.provider_metadata.get("usage"), dict)
    ]
    report = build_report(records, predictions, domain_by_record_id=domains)
    return {
        "provider": arm["provider"],
        "route": arm["route"],
        "requested_model": arm["requested_model"],
        "surfaced_model_ids": surfaced,
        "record_count": len(records),
        "resolved_count": len(resolved),
        "correct_count": correct,
        "resolved_coverage": len(resolved) / len(records) if records else 0.0,
        "unresolved_rate": (len(records) - len(resolved)) / len(records) if records else 0.0,
        "accuracy": correct / len(resolved) if resolved else None,
        "accuracy_wilson_95": _wilson(correct, len(resolved)),
        "native_probability_count": sum(prediction.probabilities is not None for prediction in predictions),
        "usage_metadata_count": len(usage),
        "status_counts": dict(sorted(Counter(prediction.execution_status.value for prediction in predictions).items())),
        "error_kinds": dict(sorted(error_kinds.items())),
        "metrics": report,
    }


def _differential(
    records: list[JudgeRecord], predictions: dict[str, list[JudgePrediction]]
) -> dict[str, Any]:
    by_arm = {
        arm: {prediction.record_id: prediction for prediction in values}
        for arm, values in predictions.items()
    }
    arms = sorted(predictions)
    pairs: dict[str, dict[str, Any]] = {}
    for left_index, left in enumerate(arms):
        for right in arms[left_index + 1 :]:
            comparable = 0
            agreement = 0
            for record in records:
                first = by_arm[left][record.record_id]
                second = by_arm[right][record.record_id]
                if (
                    first.execution_status is ExecutionStatus.OK
                    and second.execution_status is ExecutionStatus.OK
                    and first.label is not None
                    and second.label is not None
                ):
                    comparable += 1
                    agreement += int(first.label == second.label)
            pairs[f"{left}__vs__{right}"] = {
                "comparable_count": comparable,
                "agreement_count": agreement,
                "agreement_rate": agreement / comparable if comparable else None,
            }
    return {"arms": arms, "pairs": pairs}


def _checksums(root: Path) -> None:
    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "checksums.sha256":
            continue
        entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}")
    (root / "checksums.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")


def _run(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    prediction_dir = output / "predictions"
    prediction_dir.mkdir()
    pool = Path(args.pool)
    selected_rows, records, domains = _load_pool(pool, args.partition, args.limit, args.record_ids_file)
    environment = {**_load_dotenv(Path(args.env_file) if args.env_file else None), **os.environ}
    selected_arms = tuple(args.models.split(",")) if args.models else ("grok", "luna", "qwen_flash")
    unknown = sorted(set(selected_arms) - set(ARMS))
    if unknown:
        raise ValueError(f"unknown arm(s): {unknown}")
    predictions: dict[str, list[JudgePrediction]] = {}
    reports: dict[str, Any] = {}
    for arm_id in selected_arms:
        arm = ARMS[arm_id]
        if arm_id == "grok":
            arm_predictions = _run_grok_build_arm(
                records,
                arm_id=arm_id,
                model=arm["requested_model"],
                route=arm["route"],
                environment=environment,
                timeout=args.timeout,
            )
        elif arm["provider"] == "codex":
            arm_predictions = _run_codex_arm(
                records,
                arm_id=arm_id,
                model=arm["requested_model"],
                route=arm["route"],
                environment=environment,
                timeout=args.timeout,
                workers=args.workers,
            )
        else:
            arm_predictions = _run_qwen_arm(
                records,
                arm_id=arm_id,
                model=arm["requested_model"],
                route=arm["route"],
                environment=environment,
                timeout=args.timeout,
            )
        predictions[arm_id] = arm_predictions
        (prediction_dir / f"{arm_id}.jsonl").write_text(
            "".join(prediction.model_dump_json() + "\n" for prediction in arm_predictions),
            encoding="utf-8",
        )
        reports[arm_id] = _arm_summary(records, arm_predictions, domains, arm)

    manifest = json.loads((pool / "pool-manifest.json").read_text(encoding="utf-8"))
    results = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output.name,
        "status": "completed_with_provider_statuses",
        "partition": args.partition,
        "source_pool": {
            "records_fingerprint": manifest["records_fingerprint"],
            "blind_record_ids_fingerprint": manifest["blind_record_ids_fingerprint"],
            "typed_question_spec_fingerprint": manifest["typed_question_spec_fingerprint"],
        },
        "record_count": len(records),
        "record_ids_unique": len({record.record_id for record in records}) == len(records),
        "provider_pool_order_sha256": hashlib.sha256(
            "\n".join(row["record"]["record_id"] for row in selected_rows).encode("utf-8")
        ).hexdigest(),
        "arms": reports,
        "differential": _differential(records, predictions),
        "environment": {"platform": platform.platform(), "python": platform.python_version()},
        "created_at_utc": datetime.now(UTC).isoformat(),
    }
    (output / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "differential.json").write_text(
        json.dumps(results["differential"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "provider-status.json").write_text(
        json.dumps(
            {
                "experiment_id": EXPERIMENT_ID,
                "run_id": output.name,
                "partition": args.partition,
                "arms": {
                    arm_id: {
                        "provider": report["provider"],
                        "route": report["route"],
                        "requested_model": report["requested_model"],
                        "surfaced_model_ids": report["surfaced_model_ids"],
                        "status_counts": report["status_counts"],
                        "error_kinds": report["error_kinds"],
                    }
                    for arm_id, report in reports.items()
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        f"# {EXPERIMENT_ID} — {output.name}",
        "",
        f"Partition: `{args.partition}`; matched records: `{len(records)}`.",
        "",
        "| Arm | Requested model | Surfaced IDs | Resolved | Coverage | Accuracy | Wilson 95% | Statuses |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for arm_id, report in reports.items():
        surfaced = ", ".join(report["surfaced_model_ids"]) or "(none surfaced)"
        lines.append(
            f"| `{arm_id}` | `{report['requested_model']}` | `{surfaced}` | "
            f"{report['resolved_count']}/{report['record_count']} | {report['resolved_coverage']:.4f} | "
            f"{report['accuracy']} | `{report['accuracy_wilson_95']}` | `{report['status_counts']}` |"
        )
    lines.extend(
        [
            "",
            "Provider failures, rate limits, parse errors, and skipped records remain unresolved and receive no fallback label.",
            "Native probability and risk/coverage metrics are reported only when a valid probability map is returned.",
            "",
            f"Same-record agreement: `{json.dumps(results['differential']['pairs'], sort_keys=True)}`.",
        ]
    )
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _checksums(output)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", type=Path, default=POOL)
    parser.add_argument("--partition", choices=("public_selection", "blind_holdout", "all"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--record-ids-file", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--models", help="comma-separated arm IDs; default: grok,luna,qwen_flash")
    args = parser.parse_args()
    if args.limit < 0 or args.workers <= 0:
        raise SystemExit("--limit must be non-negative and --workers must be positive")
    result = _run(args)
    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "run_id": result["run_id"],
                "partition": result["partition"],
                "record_count": result["record_count"],
                "arms": {arm: report["status_counts"] for arm, report in result["arms"].items()},
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
