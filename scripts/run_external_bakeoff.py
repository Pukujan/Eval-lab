"""Run the bounded TASK-0007 external-provider bakeoff."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from eval_lab.datasets.arc import ArcSourceMetadata, build_arc_dataset
from eval_lab.datasets.synthetic import generate_synthetic_fixtures
from eval_lab.metrics.latency import latency_summary
from eval_lab.reporting import build_report
from eval_lab.schema import ExecutionStatus, JudgePrediction, JudgeRecord, JudgmentMode

EXPERIMENT_ID = "EXP-20260920-003-external-judge-bakeoff"
TASK6_MANIFEST = Path("experiments/EXP-20260920-002-qwen-0-6b-calibrated/manifest.json")
ARC_MANIFEST = Path("manifests/arc-challenge-slice.json")
YOLO_MODEL = "qwen3.8-flash"
FREE_MODELS = ("opencode/nemotron-3.5-lightning-free", "opencode/mimo-v2.5-free")
GROK_MODEL = "opencode/grok-4.6"
ALL_MODELS = ("yolo-auto/qwen3.8-flash", *FREE_MODELS, GROK_MODEL)


@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    provider: str
    model: str
    kind: str


PROVIDERS = {
    "yolo-auto/qwen3.8-flash": ProviderSpec(
        "yolo-auto/qwen3.8-flash", "yolo-auto", YOLO_MODEL, "yolo"
    ),
    "opencode/nemotron-3.5-lightning-free": ProviderSpec(
        "opencode/nemotron-3.5-lightning-free",
        "opencode",
        "opencode/nemotron-3.5-lightning-free",
        "opencode",
    ),
    "opencode/mimo-v2.5-free": ProviderSpec(
        "opencode/mimo-v2.5-free", "opencode", "opencode/mimo-v2.5-free", "opencode"
    ),
    "opencode/grok-4.6": ProviderSpec(
        "opencode/grok-4.6", "opencode", "opencode/grok-4.6", "opencode"
    ),
}


def _load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _fetch_arc_rows(manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    wanted = set(manifest["source_problem_ids"])
    rows_by_split: dict[str, list[dict[str, Any]]] = {"train": [], "validation": [], "test": []}
    for upstream_split in rows_by_split:
        response = httpx.get(
            "https://datasets-server.huggingface.co/rows",
            params={
                "dataset": manifest["dataset_id"],
                "config": manifest["config"],
                "split": upstream_split,
                "offset": 0,
                "length": 100,
                "revision": manifest["resolved_revision"],
            },
            timeout=30,
        )
        response.raise_for_status()
        rows_by_split[upstream_split] = [
            item["row"]
            for item in response.json().get("rows", [])
            if item["row"].get("id") in wanted
        ]
    found = {str(row["id"]) for rows in rows_by_split.values() for row in rows}
    if found != wanted:
        raise RuntimeError(f"ARC manifest IDs not fully retrievable: missing={sorted(wanted - found)}")
    return rows_by_split


def _load_records() -> tuple[list[JudgeRecord], dict[str, str], dict[str, Any]]:
    task6_manifest = json.loads(TASK6_MANIFEST.read_text(encoding="utf-8"))
    arc_manifest = json.loads(ARC_MANIFEST.read_text(encoding="utf-8"))
    metadata = ArcSourceMetadata(
        dataset_id=arc_manifest["dataset_id"],
        config=arc_manifest["config"],
        license=arc_manifest["license"],
        requested_revision=arc_manifest["requested_revision"],
        resolved_revision=arc_manifest["resolved_revision"],
        canonicalization_version=arc_manifest["canonicalization_version"],
        split_policy=arc_manifest["split_policy"],
        split_seed=arc_manifest["split_seed"],
        validation_dev_fraction=arc_manifest["validation_dev_fraction"],
        fingerprint=arc_manifest["fingerprint"],
    )
    arc_result = build_arc_dataset(
        _fetch_arc_rows(arc_manifest), metadata=metadata.model_copy(update={"fingerprint": None})
    )
    if arc_result.fingerprint != arc_manifest["fingerprint"]:
        raise RuntimeError("retrieved ARC rows do not match committed slice fingerprint")
    fixture = generate_synthetic_fixtures()
    records_by_id = {record.record_id: record for record in fixture.records}
    records_by_id.update({record.record_id: record for record in arc_result.records})
    missing = [record_id for record_id in task6_manifest["record_ids"] if record_id not in records_by_id]
    if missing:
        raise RuntimeError(f"TASK-0006 record IDs cannot be reconstructed: {missing}")
    records = [records_by_id[record_id] for record_id in task6_manifest["record_ids"]]
    source_by_id = {source.source_problem_id: source for source in fixture.sources}
    domains = {
        record.record_id: source_by_id[record.source_problem_id].domain
        for record in records
        if record.source_problem_id in source_by_id
    }
    domains.update({record.record_id: "arc_challenge" for record in arc_result.records})
    return records, domains, {"task6_manifest": task6_manifest, "arc_manifest": arc_manifest}


def _prompt(record: JudgeRecord) -> str:
    criteria = "\n".join(
        f"- {item.criterion_id}: {item.description}" for item in record.rubric
    )
    candidates = f"Candidate A:\n{record.candidate_a}"
    if record.mode is JudgmentMode.PAIRWISE:
        candidates += f"\n\nCandidate B:\n{record.candidate_b}"
        labels = "A, B, or TIE"
    else:
        labels = "pass or fail"
    return (
        "You are an evaluation judge. Use the question and rubric to classify the candidates.\n"
        f"Return exactly one JSON object with a label from {{{labels}}}; do not include markdown or explanation.\n\n"
        f"Question:\n{record.prompt}\n\nRubric:\n{criteria}\n\n{candidates}\n"
        "JSON:"
    )


def _legal_labels(record: JudgeRecord) -> set[str]:
    return {"A", "B", "TIE"} if record.mode is JudgmentMode.PAIRWISE else {"pass", "fail"}


def _parse_label(text: str, record: JudgeRecord) -> str | None:
    legal = _legal_labels(record)
    for match in re.finditer(r"""["']label["']\s*:\s*["']([^"']+)""", text, re.IGNORECASE):
        candidate = match.group(1).strip().upper() if record.mode is JudgmentMode.PAIRWISE else match.group(1).strip().lower()
        if candidate in legal:
            return candidate
    normalized = text.upper() if record.mode is JudgmentMode.PAIRWISE else text.lower()
    tokens = re.findall(r"\b(?:A|B|TIE|PASS|FAIL)\b", normalized)
    for token in reversed(tokens):
        candidate = token if record.mode is JudgmentMode.PAIRWISE else token.lower()
        if candidate in legal:
            return candidate
    return None


def _prediction(
    record: JudgeRecord,
    *,
    spec: ProviderSpec,
    status: ExecutionStatus,
    started: float,
    label: str | None = None,
    metadata: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> JudgePrediction:
    return JudgePrediction(
        record_id=record.record_id,
        judge_id=spec.provider_id,
        protocol_version="external-forced-choice-v1",
        label=label,
        probabilities=None,
        raw_scores=None,
        execution_status=status,
        latency_ms=(time.perf_counter() - started) * 1000,
        provider_metadata={
            "provider": spec.provider,
            "model_id": spec.model,
            "context_cap": 4096,
            **(metadata or {}),
        },
        error=error,
    )


def _skipped(record: JudgeRecord, spec: ProviderSpec, reason: str) -> JudgePrediction:
    return _prediction(
        record,
        spec=spec,
        status=ExecutionStatus.SKIPPED,
        started=time.perf_counter(),
        metadata={"stopped_after_provider_failure": True},
        error={"kind": "arm_stopped", "reason": reason},
    )


def _yolo_one(
    record: JudgeRecord,
    spec: ProviderSpec,
    *,
    env: dict[str, str],
    timeout: float,
) -> JudgePrediction:
    started = time.perf_counter()
    base_url = env.get("QWEN_API_URL", "https://yolo-auto.com/v1").rstrip("/")
    api_key = env.get("YOLO_AUTO_API_KEY") or env.get("QWEN_API_KEY")
    if not api_key:
        return _prediction(
            record,
            spec=spec,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "missing_credential"},
        )
    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": YOLO_MODEL,
                "messages": [{"role": "user", "content": _prompt(record)}],
                "temperature": 0,
                "max_tokens": 128,
                "chat_template_kwargs": {"enable_thinking": False},
            },
            timeout=timeout,
        )
    except httpx.TimeoutException:
        return _prediction(
            record,
            spec=spec,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "timeout"},
        )
    except httpx.HTTPError as exc:
        return _prediction(
            record,
            spec=spec,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "http_error", "type": type(exc).__name__},
        )
    if response.status_code == 429:
        return _prediction(
            record,
            spec=spec,
            status=ExecutionStatus.RATE_LIMITED,
            started=started,
            error={"kind": "rate_limited", "retry_after": response.headers.get("retry-after")},
        )
    if response.status_code >= 400:
        return _prediction(
            record,
            spec=spec,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "http_status", "status_code": response.status_code},
        )
    try:
        payload = response.json()
        returned_model = str(payload.get("model", ""))
        if returned_model != YOLO_MODEL:
            return _prediction(
                record,
                spec=spec,
                status=ExecutionStatus.PROVIDER_ERROR,
                started=started,
                error={"kind": "model_identity_mismatch", "returned_model": returned_model},
            )
        content = ((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    except (ValueError, IndexError, AttributeError, TypeError):
        return _prediction(
            record,
            spec=spec,
            status=ExecutionStatus.PARSE_ERROR,
            started=started,
            error={"kind": "invalid_json_response"},
        )
    label = _parse_label(str(content), record)
    if label is None:
        return _prediction(
            record,
            spec=spec,
            status=ExecutionStatus.PARSE_ERROR,
            started=started,
            error={"kind": "label_not_found"},
        )
    return _prediction(
        record,
        spec=spec,
        status=ExecutionStatus.OK,
        started=started,
        label=label,
        metadata={"endpoint": base_url, "returned_model": returned_model},
    )


def _opencode_one(
    record: JudgeRecord,
    spec: ProviderSpec,
    *,
    env: dict[str, str],
    timeout: float,
) -> JudgePrediction:
    started = time.perf_counter()
    executable = env.get("OPENCODE_EXE") or shutil.which("opencode") or "opencode"
    try:
        result = subprocess.run(
            [
                executable,
                "run",
                "--model",
                spec.model,
                "--format",
                "json",
                "--log-level",
                "ERROR",
                "--dir",
                str(Path.cwd()),
                _prompt(record),
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, **env},
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _prediction(
            record,
            spec=spec,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "timeout"},
        )
    except OSError as exc:
        return _prediction(
            record,
            spec=spec,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "process_error", "type": type(exc).__name__},
        )
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    if result.returncode != 0:
        return _prediction(
            record,
            spec=spec,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "process_exit", "returncode": result.returncode},
        )
    label = _parse_label(output, record)
    if label is None:
        return _prediction(
            record,
            spec=spec,
            status=ExecutionStatus.PARSE_ERROR,
            started=started,
            error={"kind": "label_not_found"},
        )
    return _prediction(
        record,
        spec=spec,
        status=ExecutionStatus.OK,
        started=started,
        label=label,
        metadata={"cli": "opencode", "surfaced_model_id": spec.model},
    )


def _run_provider(
    records: list[JudgeRecord],
    spec: ProviderSpec,
    env: dict[str, str],
    timeout: float,
) -> list[JudgePrediction]:
    predictions: list[JudgePrediction] = []
    stopped_reason: str | None = None
    for record in records:
        if stopped_reason:
            predictions.append(_skipped(record, spec, stopped_reason))
            continue
        prediction = (
            _yolo_one(record, spec, env=env, timeout=timeout)
            if spec.kind == "yolo"
            else _opencode_one(record, spec, env=env, timeout=timeout)
        )
        predictions.append(prediction)
        if prediction.execution_status is ExecutionStatus.RATE_LIMITED:
            stopped_reason = prediction.error.get("kind", "provider failure") if prediction.error else "provider failure"
        elif (
            prediction.execution_status is ExecutionStatus.PROVIDER_ERROR
            and prediction.error
            and prediction.error.get("kind")
            in {"missing_credential", "timeout", "model_identity_mismatch", "process_error", "http_status"}
        ):
            stopped_reason = str(prediction.error.get("kind"))
    return predictions


def _opencode_models(env: dict[str, str]) -> tuple[str, list[str]]:
    executable = env.get("OPENCODE_EXE") or shutil.which("opencode") or "opencode"
    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            env={**os.environ, **env},
            check=False,
        )
        version = (result.stdout or result.stderr).strip()
        result = subprocess.run(
            [executable, "models"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, **env},
            check=False,
        )
        models = [line.strip() for line in (result.stdout or "").splitlines() if "/" in line]
        return version, models
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable", []


def _yolo_models(env: dict[str, str]) -> tuple[int | None, list[str]]:
    api_key = env.get("YOLO_AUTO_API_KEY") or env.get("QWEN_API_KEY")
    if not api_key:
        return None, []
    try:
        response = httpx.get(
            f"{env.get('QWEN_API_URL', 'https://yolo-auto.com/v1').rstrip('/')}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        return response.status_code, [
            str(item.get("id")) for item in payload.get("data", []) if isinstance(item, dict)
        ]
    except (httpx.HTTPError, ValueError):
        return None, []


def _load_local_predictions(record_ids: set[str]) -> dict[str, JudgePrediction]:
    path = Path("experiments/EXP-20260920-002-qwen-0-6b-calibrated/calibrated_predictions.jsonl")
    predictions: dict[str, JudgePrediction] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        prediction = JudgePrediction.model_validate_json(line)
        if prediction.record_id in record_ids:
            predictions[prediction.record_id] = prediction
    return predictions


def _coverage(predictions: list[JudgePrediction]) -> dict[str, Any]:
    by_status: dict[str, list[str]] = {}
    for prediction in predictions:
        by_status.setdefault(prediction.execution_status.value, []).append(prediction.record_id)
    return {
        "counts": {key: len(value) for key, value in sorted(by_status.items())},
        "record_ids": by_status,
    }


def _audit_payload(record: JudgeRecord, local: JudgePrediction | None, target: str) -> dict[str, Any]:
    return {
        "record_id": record.record_id,
        "target": target,
        "reference_excluded": True,
        "record": record.model_dump(mode="json", exclude={"gold"}),
        "local_prediction": local.model_dump(mode="json") if local else None,
    }


def _write_jsonl(path: Path, values: list[dict[str, Any] | JudgePrediction]) -> None:
    payloads = [
        value.model_dump(mode="json") if isinstance(value, JudgePrediction) else value
        for value in values
    ]
    path.write_text(
        "\n".join(json.dumps(value, sort_keys=True) for value in payloads) + "\n",
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> Path:
    output_dir = Path(args.output_dir)
    existing = {path.name for path in output_dir.iterdir()} if output_dir.exists() else set()
    if existing - {"README.md", "experiment.yaml"}:
        raise FileExistsError(f"refusing to overwrite existing experiment: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    env = {**_load_dotenv(Path(args.env_file)), **os.environ}
    all_records, domains, source_metadata = _load_records()
    records = all_records[: args.limit]
    selected_models = tuple(args.models.split(",")) if args.models else ALL_MODELS
    specs = [PROVIDERS[model] for model in selected_models]
    provider_predictions = {
        spec.provider_id: _run_provider(records, spec, env, args.timeout) for spec in specs
    }
    local_by_id = _load_local_predictions({record.record_id for record in records})
    local_predictions = [local_by_id[record.record_id] for record in records]
    provider_reports: dict[str, Any] = {}
    for spec in specs:
        predictions = provider_predictions[spec.provider_id]
        local_labels = {record_id: prediction.label for record_id, prediction in local_by_id.items()}
        agreement = sum(
            prediction.execution_status is ExecutionStatus.OK
            and prediction.label == local_labels.get(prediction.record_id)
            for prediction in predictions
        )
        provider_reports[spec.provider_id] = {
            "provider": spec.provider,
            "model": spec.model,
            "coverage": _coverage(predictions),
            "report": build_report(records, predictions, domain_by_record_id=domains),
            "agreement_with_task6_local_ok": agreement,
        }
    local_report = build_report(records, local_predictions, domain_by_record_id=domains)
    census_version, opencode_models = _opencode_models(env)
    yolo_status, yolo_models = _yolo_models(env)
    uncertainty = sorted(
        records,
        key=lambda record: (
            max(local_by_id[record.record_id].probabilities.values())
            if local_by_id[record.record_id].probabilities
            else 1.0,
            record.record_id,
        ),
    )
    disagreements: dict[str, int] = {}
    for record in records:
        labels = {
            prediction.label
            for predictions in provider_predictions.values()
            for prediction in predictions
            if prediction.record_id == record.record_id
            and prediction.execution_status is ExecutionStatus.OK
        }
        local_label = local_by_id[record.record_id].label
        disagreements[record.record_id] = sum(label != local_label for label in labels)
    hard = sorted(records, key=lambda record: (-disagreements[record.record_id], record.record_id))
    luna_batch = [
        _audit_payload(record, local_by_id.get(record.record_id), "Luna")
        for record in uncertainty[: min(10, len(uncertainty))]
    ]
    sol_batch = [
        _audit_payload(record, local_by_id.get(record.record_id), "Sol")
        for record in hard[: min(10, len(hard))]
    ]
    all_predictions = [
        prediction
        for predictions in provider_predictions.values()
        for prediction in predictions
    ]
    census = {
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "opencode_cli_version": census_version,
        "opencode_models": opencode_models,
        "required_free_models_present": {model: model in opencode_models for model in FREE_MODELS},
        "supergrok_model": GROK_MODEL,
        "yolo_auto_models_status": yolo_status,
        "yolo_auto_models": yolo_models,
        "requested_arms": list(selected_models),
    }
    results = {
        "experiment_id": EXPERIMENT_ID,
        "record_count": len(records),
        "record_ids": [record.record_id for record in records],
        "identical_record_ids": True,
        "provider_reports": provider_reports,
        "task6_local_report": local_report,
        "provider_failure_summary": {
            provider_id: details["coverage"]["counts"]
            for provider_id, details in provider_reports.items()
        },
        "audit_batches": {"luna_count": len(luna_batch), "sol_count": len(sol_batch)},
    }
    report_lines = [
        "# TASK-0007 External Judge and Teacher Bakeoff",
        "",
        f"Frozen records: {len(records)}; identical record IDs claimed: {results['identical_record_ids']}.",
        "",
        "## Provider census",
        "",
        f"- OpenCode CLI: {census_version}",
        f"- YOLO-Auto /models status: {yolo_status}; exact qwen3.8-flash present: {YOLO_MODEL in yolo_models}",
        f"- Required free arms present: {census['required_free_models_present']}",
        "",
        "## Results",
        "",
        "| Provider/model | OK | Rate limited | Provider error | Parse error | Skipped | Agreement with TASK-0006 local |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for provider_id, details in provider_reports.items():
        counts = details["coverage"]["counts"]
        report_lines.append(
            f"| {provider_id} | {counts.get('ok', 0)} | {counts.get('rate_limited', 0)} | "
            f"{counts.get('provider_error', 0)} | {counts.get('parse_error', 0)} | "
            f"{counts.get('skipped', 0)} | {details['agreement_with_task6_local_ok']} |"
        )
    report_lines.extend(
        [
            "",
            "Provider failures are retained as execution states and excluded from wrong-label metrics. Model outputs are not objective gold.",
            "",
            f"Luna audit batch: {len(luna_batch)} records. Sol hard-disagreement batch: {len(sol_batch)} records.",
            "",
            "## Limitations",
            "",
            "The selected slice is small and public/synthetic. Text-only external responses do not expose calibrated probabilities, so probability metrics are unavailable for those arms. Subscription and provider availability is an execution condition recorded in the artifacts.",
        ]
    )
    _write_jsonl(output_dir / "predictions.jsonl", all_predictions)
    _write_jsonl(output_dir / "luna_audit_batch.jsonl", luna_batch)
    _write_jsonl(output_dir / "sol_hard_disagreement_batch.jsonl", sol_batch)
    (output_dir / "provider_census.json").write_text(
        json.dumps(census, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    run_manifest = {
        "id": EXPERIMENT_ID,
        "status": "completed",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "code_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip(),
        "seed": 20250920,
        "context_limit": 4096,
        "dataset": {
            "task6_manifest": str(TASK6_MANIFEST),
            "arc_fingerprint": source_metadata["arc_manifest"]["fingerprint"],
            "record_ids": [record.record_id for record in records],
        },
        "providers": list(selected_models),
        "record_count": len(records),
        "latency": latency_summary(
            [prediction.latency_ms for prediction in all_predictions if prediction.latency_ms is not None]
        ),
        "runtime": {"platform": platform.platform(), "python": platform.python_version()},
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(run_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--models", default=None)
    parser.add_argument(
        "--output-dir", default="experiments/EXP-20260920-003-external-judge-bakeoff"
    )
    args = parser.parse_args()
    print(run(args))


if __name__ == "__main__":
    main()
