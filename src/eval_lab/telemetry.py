"""Run telemetry ledger for every eval run (TASK-0062).

Eval runs are committed under ``experiments/`` in several different directory
conventions and their ``results.json`` files expose different top-level keys.
This module derives one uniform record per run unit so the whole lab can be
queried and audited in one place.

Design rules (see ``tasks/TASK-0062-run-telemetry.md`` for the rationale):

* One record per run unit; the unique key is the repo-relative POSIX
  ``run_path`` (the ``(experiment_id, run_id)`` tuple is *not* unique, because
  EXP-025 reuses ``run_id`` across its groups).
* Nullable fields stay ``null``; a metric is never coerced to ``0``. Floats are
  copied verbatim. Non-finite numbers are treated as absent.
* Deterministic: records are sorted by ``run_path`` and serialized with sorted
  keys, ``\\n`` line endings, and no generated timestamp, so regenerating the
  ledger produces identical bytes on any platform. Hashes are taken over
  LF-normalized content (see :func:`sha256_file`).
* Derivation is offline and reads committed artifacts only; it makes no model or
  provider calls and hand-types no numbers.
* Compute/Colab telemetry (accelerator, tokens/s, VRAM) is out of scope here and
  lives in ``docs/compute/colab-cli.md``.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
EXPERIMENTS_DIR = "experiments"
RUNS_DIR = "runs"
DIAGNOSTICS_DIR = "diagnostics"
EXPERIMENT_DIR_RE = re.compile(r"^EXP-\d{8}-\d{3}-[a-z0-9-]+$")
QUARANTINE_MARKERS = ("paused", "quarantine", "abandoned")

STRUCTURE_KEYS = (
    "has_metrics",
    "has_aggregate",
    "has_arms",
    "arms_count",
    "has_arm_accuracy",
    "has_partitions",
    "has_model_arms",
    "has_latency",
    "has_elapsed_seconds",
    "has_cost",
    "has_code_commit",
)


def sha256_file(path: Path) -> str:
    """SHA-256 of the file content with CRLF normalized to LF.

    Git checks text files out with the platform's line endings (CRLF on a
    Windows checkout with ``core.autocrlf=true``), so hashing raw working-tree
    bytes would make the ledger differ between a Windows and a Linux checkout of
    the same commit. Normalizing to LF makes the hash equal to the hash of the
    committed blob content, so it is stable across platforms.
    """
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        result = float(value)
        if math.isfinite(result):
            return result
    return None


def _integer(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _resolve_accuracy(doc: Mapping[str, Any]) -> tuple[float | None, str | None]:
    metrics = doc.get("metrics")
    if isinstance(metrics, Mapping):
        value = _number(metrics.get("accuracy"))
        if value is not None:
            return value, "metrics.accuracy"
    aggregate = doc.get("aggregate")
    if isinstance(aggregate, Mapping):
        inner = aggregate.get("metrics")
        if isinstance(inner, Mapping):
            value = _number(inner.get("accuracy"))
            if value is not None:
                return value, "aggregate.metrics.accuracy"
    value = _number(doc.get("accuracy"))
    if value is not None:
        return value, "accuracy"
    correct = _integer(doc.get("correct_count"))
    resolved = _integer(doc.get("resolved_count"))
    if correct is not None and resolved is not None and resolved > 0:
        return correct / resolved, "correct_count/resolved_count"
    return None, None


def _resolve_ci(doc: Mapping[str, Any]) -> dict[str, float | None] | None:
    ci = doc.get("accuracy_95_ci")
    if isinstance(ci, Mapping):
        low = _number(ci.get("lower"))
        high = _number(ci.get("upper"))
        if low is not None or high is not None:
            return {"low": low, "high": high}
    for key in ("accuracy_wilson_95", "accuracy_95_wilson"):
        bounds = doc.get(key)
        if isinstance(bounds, list) and len(bounds) == 2:
            low = _number(bounds[0])
            high = _number(bounds[1])
            if low is not None or high is not None:
                return {"low": low, "high": high}
    return None


def _resolve_record_count(doc: Mapping[str, Any]) -> int | None:
    for key in ("record_count", "total_count"):
        value = _integer(doc.get(key))
        if value is not None:
            return value
    aggregate = doc.get("aggregate")
    if isinstance(aggregate, Mapping):
        return _integer(aggregate.get("count"))
    return None


def _resolve_resolved_count(doc: Mapping[str, Any]) -> int | None:
    for key in ("resolved_count", "successful_count"):
        value = _integer(doc.get(key))
        if value is not None:
            return value
    return None


def _resolve_status_counts(doc: Mapping[str, Any]) -> dict[str, int]:
    raw = doc.get("status_counts")
    if not isinstance(raw, Mapping):
        return {}
    counts: dict[str, int] = {}
    for key, value in raw.items():
        amount = _integer(value)
        if isinstance(key, str) and amount is not None:
            counts[key] = amount
    return dict(sorted(counts.items()))


def _structure(doc: Mapping[str, Any]) -> dict[str, Any]:
    arms = doc.get("arms")
    arms_count: int | None = len(arms) if isinstance(arms, Mapping) else None
    arm_accuracy = False
    if isinstance(arms, Mapping):
        arm_accuracy = any(
            isinstance(arm, Mapping) and _number(arm.get("accuracy")) is not None
            for arm in arms.values()
        )
    return {
        "has_metrics": isinstance(doc.get("metrics"), Mapping),
        "has_aggregate": isinstance(doc.get("aggregate"), Mapping),
        "has_arms": isinstance(arms, Mapping),
        "arms_count": arms_count,
        "has_arm_accuracy": arm_accuracy,
        "has_partitions": isinstance(doc.get("partitions"), Mapping),
        "has_model_arms": isinstance(doc.get("model_arms"), Mapping),
        "has_latency": "latency" in doc or "latency_ms" in doc,
        "has_elapsed_seconds": _number(doc.get("elapsed_seconds")) is not None,
        "has_cost": _number(doc.get("actual_cost")) is not None,
        "has_code_commit": isinstance(doc.get("code_commit"), str),
    }


def _empty_structure() -> dict[str, Any]:
    return {
        "has_metrics": False,
        "has_aggregate": False,
        "has_arms": False,
        "arms_count": None,
        "has_arm_accuracy": False,
        "has_partitions": False,
        "has_model_arms": False,
        "has_latency": False,
        "has_elapsed_seconds": False,
        "has_cost": False,
        "has_code_commit": False,
    }


def _scope_for(directory: Path, experiment_dir: Path) -> str:
    if directory == experiment_dir:
        return "experiment"
    if directory.parent == experiment_dir / RUNS_DIR:
        return "run"
    if directory.parent.parent == experiment_dir / RUNS_DIR:
        return "nested_run"
    if directory.parent == experiment_dir / DIAGNOSTICS_DIR:
        return "diagnostic"
    return "child_run"


def _is_quarantined(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in QUARANTINE_MARKERS)


def _base_record(
    root: Path, experiment_dir: Path, directory: Path, has_results: bool
) -> dict[str, Any]:
    scope = _scope_for(directory, experiment_dir)
    run_id = None if scope == "experiment" else directory.name
    return {
        "schema_version": SCHEMA_VERSION,
        "run_path": directory.relative_to(root).as_posix(),
        "scope": scope,
        "experiment": experiment_dir.name,
        "experiment_id": experiment_dir.name,
        "experiment_id_source": "path",
        "run_id": run_id,
        "run_id_source": None if run_id is None else "path",
        "partition": None,
        "provider": None,
        "model": None,
        "has_results": has_results,
        "results_sha256": None,
        "created_at_utc": None,
        "record_count": None,
        "resolved_count": None,
        "status_counts": {},
        "accuracy": None,
        "accuracy_ci": None,
        "accuracy_source": None,
        "structure": _empty_structure(),
        "completeness": "partial",
    }


def _read_doc(path: Path) -> dict[str, Any] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        raw: object = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    return {str(key): value for key, value in raw.items()}


def _record(root: Path, experiment_dir: Path, directory: Path, has_results: bool) -> dict[str, Any]:
    row = _base_record(root, experiment_dir, directory, has_results)
    if not has_results:
        row["completeness"] = "quarantined" if _is_quarantined(directory.name) else "partial"
        return row

    results = directory / "results.json"
    row["results_sha256"] = sha256_file(results)
    doc = _read_doc(results)
    if doc is None:
        row["completeness"] = "quarantined"
        return row

    row["completeness"] = "complete"
    embedded_experiment = _text(doc.get("experiment_id"))
    if embedded_experiment is not None:
        row["experiment_id"] = embedded_experiment
        row["experiment_id_source"] = "embedded"
    embedded_run = _text(doc.get("run_id"))
    if embedded_run is not None:
        row["run_id"] = embedded_run
        row["run_id_source"] = "embedded"
    row["partition"] = _text(doc.get("partition"))
    row["provider"] = _text(doc.get("provider"))
    row["model"] = _text(doc.get("model")) or _text(doc.get("requested_model"))
    row["created_at_utc"] = _text(doc.get("created_at_utc"))
    row["record_count"] = _resolve_record_count(doc)
    row["resolved_count"] = _resolve_resolved_count(doc)
    row["status_counts"] = _resolve_status_counts(doc)
    accuracy, source = _resolve_accuracy(doc)
    row["accuracy"] = accuracy
    row["accuracy_source"] = source
    row["accuracy_ci"] = _resolve_ci(doc)
    row["structure"] = _structure(doc)
    return row


def _records_for_experiment(root: Path, experiment_dir: Path) -> list[dict[str, Any]]:
    records = [
        _record(root, experiment_dir, results.parent, True)
        for results in sorted(experiment_dir.rglob("results.json"))
    ]
    runs_dir = experiment_dir / RUNS_DIR
    if not runs_dir.is_dir():
        return records
    for child in sorted(entry for entry in runs_dir.iterdir() if entry.is_dir()):
        if (child / "results.json").is_file():
            continue
        # A directory holding nested arm runs is a container; those runs already
        # appear as nested_run records carrying the group in their run_path.
        if any((grandchild / "results.json").is_file() for grandchild in child.iterdir()):
            continue
        records.append(_record(root, experiment_dir, child, False))
    return records


def build_records(root: Path) -> list[dict[str, Any]]:
    """Derive one telemetry record per run unit under ``root/experiments``."""
    root = Path(root)
    base = root / EXPERIMENTS_DIR
    records: list[dict[str, Any]] = []
    if not base.is_dir():
        return records
    for experiment_dir in sorted(
        entry for entry in base.iterdir() if entry.is_dir() and EXPERIMENT_DIR_RE.match(entry.name)
    ):
        records.extend(_records_for_experiment(root, experiment_dir))
    records.sort(key=lambda record: record["run_path"])
    return records


def dumps_jsonl(records: Iterable[Mapping[str, Any]]) -> str:
    """Serialize records deterministically: sorted keys, LF endings, no NaN."""
    lines = [
        json.dumps(
            record, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        )
        for record in records
    ]
    return "".join(line + "\n" for line in lines)


def _coverage(records: list[dict[str, Any]], predicate: Any) -> int:
    return sum(1 for record in records if predicate(record))


def compute_findings(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute repository-wide findings from ledger records (no hand-typed numbers)."""
    by_scope: dict[str, int] = {}
    by_completeness: dict[str, int] = {}
    by_experiment: dict[str, dict[str, int]] = {}
    status_totals: dict[str, int] = {}
    providers: dict[str, int] = {}
    run_id_uses: dict[str, set[str]] = {}

    for record in records:
        scope = str(record["scope"])
        by_scope[scope] = by_scope.get(scope, 0) + 1
        completeness = str(record["completeness"])
        by_completeness[completeness] = by_completeness.get(completeness, 0) + 1

        experiment = str(record["experiment"])
        bucket = by_experiment.setdefault(
            experiment,
            {
                "rows": 0,
                "with_results": 0,
                "complete": 0,
                "partial": 0,
                "quarantined": 0,
                "accuracy": 0,
            },
        )
        bucket["rows"] += 1
        if record["has_results"]:
            bucket["with_results"] += 1
        bucket[completeness] += 1
        if record["accuracy"] is not None:
            bucket["accuracy"] += 1

        for key, value in dict(record["status_counts"]).items():
            status_totals[key] = status_totals.get(key, 0) + int(value)
        provider = record["provider"]
        if isinstance(provider, str):
            providers[provider] = providers.get(provider, 0) + 1
        run_id = record["run_id"]
        if isinstance(run_id, str):
            run_id_uses.setdefault(run_id, set()).add(experiment)

    with_results = [record for record in records if record["has_results"]]
    created = sorted(
        str(record["created_at_utc"]) for record in records if record["created_at_utc"] is not None
    )
    reused_run_ids = sorted(
        run_id for run_id, experiments in run_id_uses.items() if len(experiments) > 1
    )
    structure_totals = {
        key: _coverage(records, lambda record, k=key: bool(record["structure"][k]))
        for key in STRUCTURE_KEYS
        if key != "arms_count"
    }
    arms_total = sum(
        int(record["structure"]["arms_count"] or 0)
        for record in records
        if record["structure"]["arms_count"] is not None
    )

    return {
        "totals": {
            "rows": len(records),
            "with_results": len(with_results),
            "without_results": len(records) - len(with_results),
            "accuracy_rows": _coverage(records, lambda record: record["accuracy"] is not None),
            "results_sha256_rows": _coverage(
                records, lambda record: record["results_sha256"] is not None
            ),
            "created_at_rows": len(created),
            "arms_total": arms_total,
        },
        "by_scope": dict(sorted(by_scope.items())),
        "by_completeness": dict(sorted(by_completeness.items())),
        "by_experiment": dict(sorted(by_experiment.items())),
        "status_totals": dict(sorted(status_totals.items())),
        "providers": dict(sorted(providers.items())),
        "created_at_range": {"first": created[0], "last": created[-1]} if created else None,
        "reused_run_ids": reused_run_ids,
        "structure_coverage": structure_totals,
        "missing_results": sorted(
            str(record["run_path"]) for record in records if not record["has_results"]
        ),
    }


def render_findings(records: list[dict[str, Any]]) -> str:
    """Render ``telemetry/FINDINGS.md`` from ledger records."""
    findings = compute_findings(records)
    totals = findings["totals"]
    lines: list[str] = []
    lines.append("# Run telemetry findings")
    lines.append("")
    lines.append(
        "Generated by `scripts/run_telemetry.py findings` from `telemetry/runs.v1.jsonl`. "
        "Do not edit by hand; no number here is hand-typed."
    )
    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    lines.append("| metric | value |")
    lines.append("| --- | ---: |")
    lines.append(f"| run units | {totals['rows']} |")
    lines.append(f"| with results.json | {totals['with_results']} |")
    lines.append(f"| without results.json | {totals['without_results']} |")
    lines.append(f"| rows with resolved accuracy | {totals['accuracy_rows']} |")
    lines.append(f"| rows with created_at_utc | {totals['created_at_rows']} |")
    lines.append(f"| arms across arms-comparison runs | {totals['arms_total']} |")
    lines.append("")
    lines.append("## By scope")
    lines.append("")
    lines.append("| scope | rows |")
    lines.append("| --- | ---: |")
    for scope, count in findings["by_scope"].items():
        lines.append(f"| {scope} | {count} |")
    lines.append("")
    lines.append("## By completeness")
    lines.append("")
    lines.append("| completeness | rows |")
    lines.append("| --- | ---: |")
    for completeness, count in findings["by_completeness"].items():
        lines.append(f"| {completeness} | {count} |")
    lines.append("")
    lines.append("## Structural coverage")
    lines.append("")
    lines.append("| field | rows |")
    lines.append("| --- | ---: |")
    for key, count in findings["structure_coverage"].items():
        lines.append(f"| {key} | {count} |")
    lines.append("")
    lines.append("## Per experiment")
    lines.append("")
    lines.append(
        "| experiment | rows | with results | complete | partial | quarantined | accuracy rows |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for experiment, bucket in findings["by_experiment"].items():
        lines.append(
            f"| {experiment} | {bucket['rows']} | {bucket['with_results']} | "
            f"{bucket['complete']} | {bucket['partial']} | {bucket['quarantined']} | {bucket['accuracy']} |"
        )
    lines.append("")
    if findings["created_at_range"] is not None:
        lines.append("## Created-at range")
        lines.append("")
        lines.append(f"- first: `{findings['created_at_range']['first']}`")
        lines.append(f"- last: `{findings['created_at_range']['last']}`")
        lines.append("")
    lines.append("## Providers")
    lines.append("")
    if findings["providers"]:
        lines.append("| provider | rows |")
        lines.append("| --- | ---: |")
        for provider, count in findings["providers"].items():
            lines.append(f"| {provider} | {count} |")
    else:
        lines.append("_No rows record a provider._")
    lines.append("")
    lines.append("## Status counts (summed across rows)")
    lines.append("")
    if findings["status_totals"]:
        lines.append("| status | records |")
        lines.append("| --- | ---: |")
        for status, count in findings["status_totals"].items():
            lines.append(f"| {status} | {count} |")
    else:
        lines.append("_No rows record status counts._")
    lines.append("")
    lines.append("## Runs without results.json")
    lines.append("")
    if findings["missing_results"]:
        lines.append(
            "These directories exist but hold no `results.json`; they are `partial` "
            "(predictions only) or `quarantined` (paused/abandoned)."
        )
        lines.append("")
        for path in findings["missing_results"]:
            lines.append(f"- `{path}`")
    else:
        lines.append("_Every run directory has a results.json._")
    lines.append("")
    lines.append("## Reused run_id values")
    lines.append("")
    if findings["reused_run_ids"]:
        lines.append(
            "These `run_id` values appear in more than one experiment, which is why the ledger "
            "keys on `run_path` rather than `(experiment_id, run_id)`:"
        )
        lines.append("")
        for run_id in findings["reused_run_ids"]:
            lines.append(f"- `{run_id}`")
    else:
        lines.append("_No run_id value is reused across experiments._")
    lines.append("")
    return "\n".join(lines)
