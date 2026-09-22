"""Run the preregistered Grok Build protocol ablation."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import time
import uuid
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from eval_lab.escalation.spec import build_decision_spec
from eval_lab.schema import (
    ExecutionStatus,
    JudgePrediction,
    JudgeRecord,
    JudgmentMode,
    PairwiseLabel,
)

try:
    from scripts.run_grok_luna_qwen_bakeoff import (
        _isolated_grok_leader_socket,
        _json_fragments,
        _load_dotenv,
        _load_pool,
        _nested_mappings,
        _run_streaming_process,
        _surfaced_models,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from run_grok_luna_qwen_bakeoff import (
        _isolated_grok_leader_socket,
        _json_fragments,
        _load_dotenv,
        _load_pool,
        _nested_mappings,
        _run_streaming_process,
        _surfaced_models,
    )

POOL = Path("experiments/EXP-20260921-015-grok-luna-qwen-bakeoff")
EXPERIMENT_ID = "EXP-20260922-025-grok-protocol-ablation"
VARIANTS = ("typed_schema", "explicit_schema", "semantic_schema", "explicit_no_schema")
MODELS = {"grok_46": "grok-4.6", "grok_47": "grok-4.7"}
PROTOCOL_VERSION = "grok-protocol-ablation-v1"


def _legal_labels(record: JudgeRecord) -> tuple[str, ...]:
    if record.mode is JudgmentMode.SINGLE:
        return ("pass", "fail")
    return tuple(item.value for item in PairwiseLabel)


def _semantic_labels(record: JudgeRecord) -> tuple[str, ...]:
    if record.mode is JudgmentMode.SINGLE:
        return ("CORRECT", "INCORRECT")
    return ("A_BETTER", "B_BETTER", "EQUIVALENT")


def output_schema(record: JudgeRecord, variant: str) -> str | None:
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant: {variant}")
    if variant == "explicit_no_schema":
        return None
    labels = _semantic_labels(record) if variant == "semantic_schema" else _legal_labels(record)
    return json.dumps(
        {
            "type": "object",
            "properties": {"label": {"type": "string", "enum": list(labels)}},
            "required": ["label"],
            "additionalProperties": False,
        },
        separators=(",", ":"),
    )


def _explicit_prompt(record: JudgeRecord, variant: str) -> str:
    rubric = "\n".join(f"- {item.description}" for item in record.rubric)
    if record.mode is JudgmentMode.SINGLE:
        task = "Decide whether Candidate A is objectively correct for the user prompt."
        semantics = "pass means correct; fail means incorrect."
        labels = _semantic_labels(record) if variant == "semantic_schema" else _legal_labels(record)
        label_instruction = f"The only legal labels are {', '.join(labels)}; {semantics}"
    else:
        task = "Compare Candidate A and Candidate B for the user prompt."
        semantics = "A_BETTER means A is better or more correct; B_BETTER means B is better or more correct; EQUIVALENT means they are objectively equivalent."
        labels = _semantic_labels(record) if variant == "semantic_schema" else _legal_labels(record)
        label_instruction = f"The only legal labels are {', '.join(labels)}; {semantics}"
    candidate_b = f"\n\nCANDIDATE B:\n{record.candidate_b}" if record.candidate_b is not None else ""
    return (
        "You are an objective evaluation judge. Do not use tools, web search, or outside knowledge beyond the record.\n"
        f"{task} {label_instruction}\n"
        "Return exactly one JSON object with one key, label. Do not include explanation or markdown.\n\n"
        f"RECORD ID: {record.record_id}\n\n"
        f"USER PROMPT:\n{record.prompt}\n\n"
        f"RUBRIC:\n{rubric}\n\n"
        f"CANDIDATE A:\n{record.candidate_a}{candidate_b}"
    )


def build_prompt(record: JudgeRecord, variant: str) -> str:
    """Build a provider prompt without including gold or verifier evidence."""

    if variant == "typed_schema":
        decision = build_decision_spec(record)
        labels = ", ".join(decision.legal_labels)
        payload = {"record_id": decision.record_id, **decision.provider_payload()}
        return (
            "You are a strictly typed objective evaluation judge. "
            f"Return exactly one JSON object with label set to one of [{labels}]. "
            "Do not include explanation, markdown, or additional keys.\n\n"
            + json.dumps(payload, sort_keys=True)
        )
    return _explicit_prompt(record, variant)


def canonicalize_label(value: str, record: JudgeRecord, variant: str) -> str | None:
    """Map a provider label to the canonical label or return None."""

    normalized = value.strip()
    if variant == "semantic_schema":
        mapping = {
            "CORRECT": "pass",
            "INCORRECT": "fail",
            "A_BETTER": "A",
            "B_BETTER": "B",
            "EQUIVALENT": "TIE",
        }
        canonical = mapping.get(normalized.upper())
    else:
        canonical = normalized.lower() if record.mode is JudgmentMode.SINGLE else normalized.upper()
    return canonical if canonical in _legal_labels(record) else None


def parse_provider_label(text: str, record: JudgeRecord, variant: str) -> tuple[str | None, str]:
    """Parse only provider output, never stderr or the input prompt."""

    for fragment in _json_fragments(text):
        for mapping in _nested_mappings(fragment):
            for key in ("label", "verdict", "prediction", "choice", "class", "value"):
                value = mapping.get(key)
                if isinstance(value, Mapping):
                    value = next((value.get(k) for k in ("label", "choice", "value") if k in value), None)
                if value is None:
                    continue
                canonical = canonicalize_label(str(value), record, variant)
                if canonical is not None:
                    return canonical, "json"

    marker = re.findall(r"(?:FINAL_LABEL|LABEL)\s*[:=]\s*([A-Za-z_]+)", text, flags=re.IGNORECASE)
    for value in reversed(marker):
        canonical = canonicalize_label(value, record, variant)
        if canonical is not None:
            return canonical, "marker"
    return None, "unresolved"


def selection_score(mode_metrics: Mapping[str, Mapping[str, float | None]]) -> float | None:
    values = [mode_metrics.get(mode, {}).get("accuracy") for mode in ("single", "pairwise")]
    if any(value is None for value in values):
        return None
    return sum(float(value) for value in values if value is not None) / 2.0


def _prediction(
    record: JudgeRecord,
    *,
    arm_id: str,
    model: str,
    variant: str,
    status: ExecutionStatus,
    started: float,
    label: str | None = None,
    error: dict[str, Any] | None = None,
    surfaced_model_ids: list[str] | None = None,
    parser_strategy: str = "unresolved",
    event_count: int = 0,
) -> JudgePrediction:
    return JudgePrediction(
        record_id=record.record_id,
        judge_id=model,
        protocol_version=PROTOCOL_VERSION,
        label=label,
        execution_status=status,
        latency_ms=(time.perf_counter() - started) * 1000.0,
        provider_metadata={
            "provider": "xai-grok-build-cli",
            "arm_id": arm_id,
            "variant": variant,
            "requested_model": model,
            "route": "direct_grok_build_cli_subscription",
            "parser_strategy": parser_strategy,
            "surfaced_model_ids": surfaced_model_ids or [],
            "stream_format": "grok-streaming-json",
            "event_count": event_count,
        },
        error=error,
    )


def run_one(
    record: JudgeRecord,
    *,
    arm_id: str,
    model: str,
    variant: str,
    environment: Mapping[str, str],
    timeout: float,
) -> JudgePrediction:
    started = time.perf_counter()
    executable = environment.get("GROK_EXE") or shutil.which("grok") or "grok"
    leader_socket = _isolated_grok_leader_socket()
    command = [
        executable,
        "--no-auto-update",
        "--model",
        model,
        "--session-id",
        str(uuid.uuid4()),
        "--output-format",
        "streaming-json",
    ]
    schema = output_schema(record, variant)
    if schema is not None:
        command.extend(["--json-schema", schema])
    command.extend(
        [
            "--max-turns",
            "1",
            "--disable-web-search",
            "--verbatim",
            "--no-subagents",
            "--no-plan",
            "--permission-mode",
            "dontAsk",
            "--leader-socket",
            str(leader_socket),
            f"--single={build_prompt(record, variant)}",
        ]
    )
    try:
        returncode, stdout, stderr, timed_out, event_count = _run_streaming_process(
            command, environment=dict(environment), input_text=None, timeout=timeout
        )
    except OSError as exc:
        return _prediction(
            record,
            arm_id=arm_id,
            model=model,
            variant=variant,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "process_error", "type": type(exc).__name__},
        )
    finally:
        leader_socket.unlink(missing_ok=True)
    surfaced = _surfaced_models(stdout + "\n" + stderr)
    if timed_out:
        return _prediction(
            record,
            arm_id=arm_id,
            model=model,
            variant=variant,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "timeout"},
            surfaced_model_ids=surfaced,
            event_count=event_count,
        )
    if returncode != 0:
        lower = (stdout + "\n" + stderr).lower()
        status = ExecutionStatus.RATE_LIMITED if "429" in lower or "rate limit" in lower else ExecutionStatus.PROVIDER_ERROR
        kind = "rate_limited" if status is ExecutionStatus.RATE_LIMITED else "process_exit"
        return _prediction(
            record,
            arm_id=arm_id,
            model=model,
            variant=variant,
            status=status,
            started=started,
            error={"kind": kind, "returncode": returncode},
            surfaced_model_ids=surfaced,
            event_count=event_count,
        )
    label, strategy = parse_provider_label(stdout, record, variant)
    if label is None:
        return _prediction(
            record,
            arm_id=arm_id,
            model=model,
            variant=variant,
            status=ExecutionStatus.PARSE_ERROR,
            started=started,
            error={"kind": "label_not_found"},
            surfaced_model_ids=surfaced,
            parser_strategy=strategy,
            event_count=event_count,
        )
    return _prediction(
        record,
        arm_id=arm_id,
        model=model,
        variant=variant,
        status=ExecutionStatus.OK,
        started=started,
        label=label,
        surfaced_model_ids=surfaced,
        parser_strategy=strategy,
        event_count=event_count,
    )


def _load_predictions(path: Path) -> dict[str, JudgePrediction]:
    if not path.is_file():
        return {}
    result: dict[str, JudgePrediction] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            prediction = JudgePrediction.model_validate(json.loads(line))
            if prediction.record_id in result:
                raise ValueError(f"duplicate checkpoint record ID: {prediction.record_id}")
            result[prediction.record_id] = prediction
    return result


def _summarize(records: list[JudgeRecord], predictions: Mapping[str, JudgePrediction]) -> dict[str, Any]:
    mode_metrics: dict[str, dict[str, float | int | None]] = {}
    status_counts: dict[str, int] = {}
    for mode in ("single", "pairwise"):
        mode_records = [record for record in records if record.mode.value == mode]
        resolved_pairs = [
            (record, predictions[record.record_id])
            for record in mode_records
            if predictions[record.record_id].label is not None
        ]
        correct = sum(pred.label == record.gold.label for record, pred in resolved_pairs)
        mode_metrics[mode] = {
            "record_count": len(mode_records),
            "resolved_count": len(resolved_pairs),
            "coverage": len(resolved_pairs) / len(mode_records) if mode_records else None,
            "accuracy": correct / len(resolved_pairs) if resolved_pairs else None,
        }
    for prediction in predictions.values():
        status_counts[prediction.execution_status.value] = status_counts.get(prediction.execution_status.value, 0) + 1
    latencies = sorted(pred.latency_ms for pred in predictions.values() if pred.latency_ms is not None)
    p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))] if latencies else None
    return {
        "record_count": len(records),
        "resolved_count": sum(pred.label is not None for pred in predictions.values()),
        "coverage": sum(pred.label is not None for pred in predictions.values()) / len(records) if records else None,
        "mode_metrics": mode_metrics,
        "selection_score": selection_score(mode_metrics),
        "status_counts": status_counts,
        "latency_p95_ms": p95,
    }


def run_arm(
    *,
    records: list[JudgeRecord],
    partition: str,
    output: Path,
    arm_id: str,
    model: str,
    variant: str,
    environment: Mapping[str, str],
    timeout: float,
    workers: int,
    resume: bool,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    prediction_path = output / "predictions.jsonl"
    predictions = _load_predictions(prediction_path) if resume else {}
    if set(predictions) - {record.record_id for record in records}:
        raise ValueError("checkpoint contains IDs outside the selected pool")
    pending = [record for record in records if record.record_id not in predictions]
    checkpoint = output / "progress.jsonl"
    with checkpoint.open("a", encoding="utf-8") as handle, ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    run_one,
                    record,
                    arm_id=arm_id,
                    model=model,
                    variant=variant,
                    environment=environment,
                    timeout=timeout,
                ): record
                for record in pending
            }
            for future in as_completed(futures):
                prediction = future.result()
                predictions[prediction.record_id] = prediction
                handle.write(prediction.model_dump_json() + "\n")
                handle.flush()
                os.fsync(handle.fileno())
    if set(predictions) != {record.record_id for record in records}:
        raise RuntimeError("arm did not produce terminal status for every selected record")
    prediction_path.write_text(
        "".join(predictions[record.record_id].model_dump_json() + "\n" for record in records), encoding="utf-8"
    )
    summary = _summarize(records, predictions)
    results = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output.name,
        "partition": partition,
        "arm_id": arm_id,
        "model": model,
        "variant": variant,
        "streaming": True,
        "summary": summary,
    }
    (output / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", type=Path, default=POOL)
    parser.add_argument("--partition", choices=("public_selection", "blind_holdout"), required=True)
    parser.add_argument("--record-ids-file", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--variants", default=",".join(VARIANTS))
    parser.add_argument("--models", default="grok_46")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    variants = tuple(item.strip() for item in args.variants.split(",") if item.strip())
    models = tuple(item.strip() for item in args.models.split(",") if item.strip())
    unknown_variants = sorted(set(variants) - set(VARIANTS))
    unknown_models = sorted(set(models) - set(MODELS))
    if unknown_variants or unknown_models or args.workers <= 0:
        raise SystemExit(f"unknown variants={unknown_variants}, models={unknown_models}; workers must be positive")
    _, records, _ = _load_pool(args.pool, args.partition, 0, args.record_ids_file)
    environment = {**_load_dotenv(args.env_file), **os.environ} if args.env_file else dict(os.environ)
    all_results = []
    for model_id in models:
        for variant in variants:
            output = args.output_root / f"{model_id}-{variant}"
            all_results.append(
                run_arm(
                    records=records,
                    partition=args.partition,
                    output=output,
                    arm_id=model_id,
                    model=MODELS[model_id],
                    variant=variant,
                    environment=environment,
                    timeout=args.timeout,
                    workers=args.workers,
                    resume=args.resume,
                )
            )
    print(json.dumps({"experiment_id": EXPERIMENT_ID, "runs": all_results}, sort_keys=True))


if __name__ == "__main__":
    main()
