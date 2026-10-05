"""Assemble the EXP-20261004-030 Grok harness-correction experiment bundle.

Reads the public-selection and blind-holdout run directories produced by
``scripts/run_grok_luna_qwen_bakeoff.py`` and writes the experiment-level
``results.json`` and ``report.md``.  It makes no provider calls and hand-types
no metrics: every number, including the pool fingerprints, is copied from the
run artifacts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXPERIMENT_ID = "EXP-20261004-030-grok-harness-correction"
PRIMARY_PARTITION = "blind_holdout"

_ARM_FIELDS = (
    "provider",
    "route",
    "requested_model",
    "surfaced_model_ids",
    "record_count",
    "resolved_count",
    "correct_count",
    "resolved_coverage",
    "unresolved_rate",
    "accuracy",
    "accuracy_wilson_95",
    "status_counts",
    "error_kinds",
)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _arm_view(arm: dict[str, Any]) -> dict[str, Any]:
    return {field: arm.get(field) for field in _ARM_FIELDS}


def _partition_view(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_count": run.get("record_count"),
        "arms": {arm_id: _arm_view(arm) for arm_id, arm in sorted(run.get("arms", {}).items())},
    }


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _interval(bounds: Any) -> str:
    if not isinstance(bounds, dict):
        return "NA"
    low, high = bounds.get("lower"), bounds.get("upper")
    if low is None or high is None:
        return "NA"
    return f"{low:.4f}–{high:.4f}"


def finalize(*, output: Path, public: Path, blind: Path, code_commit: str) -> dict[str, Any]:
    if (output / "results.json").exists() or (output / "report.md").exists():
        raise FileExistsError(f"refusing to overwrite finalized files in {output}")
    public_run = _read(public / "results.json")
    blind_run = _read(blind / "results.json")
    if public_run.get("partition") != "public_selection":
        raise ValueError("public run is not the public_selection partition")
    if blind_run.get("partition") != "blind_holdout":
        raise ValueError("blind run is not the blind_holdout partition")
    if (
        public_run.get("experiment_id") != EXPERIMENT_ID
        or blind_run.get("experiment_id") != EXPERIMENT_ID
    ):
        raise ValueError("run experiment_id does not match")
    source_pool = blind_run.get("source_pool") or public_run.get("source_pool")
    if not isinstance(source_pool, dict) or not source_pool:
        raise ValueError("run artifacts are missing source_pool fingerprints")

    results = {
        "experiment_id": EXPERIMENT_ID,
        "status": "completed_with_provider_statuses",
        "primary_partition": PRIMARY_PARTITION,
        "source_fingerprint": source_pool.get("records_fingerprint"),
        "blind_record_ids_fingerprint": source_pool.get("blind_record_ids_fingerprint"),
        "typed_protocol_fingerprint": source_pool.get("typed_question_spec_fingerprint"),
        "code_commit": code_commit,
        "runs": {
            "public_selection": public.relative_to(output).as_posix(),
            "blind_holdout": blind.relative_to(output).as_posix(),
        },
        "public_selection": _partition_view(public_run),
        "blind_holdout": _partition_view(blind_run),
        "method": {
            "streaming": True,
            "workers_per_arm": public_run.get("execution", {}).get("workers"),
            "prompt_delivery": "per-record --prompt-file (never inline argv)",
            "one_pass_per_record": True,
            "fallback_labels": False,
            "supersedes": ["EXP-20260921-015-grok-luna-qwen-bakeoff (Grok arms)"],
        },
    }
    (output / "results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lines = [
        f"# {EXPERIMENT_ID} — Grok Build harness correction",
        "",
        "This is an append-only correction. EXP-022 and EXP-025 are not modified. The only",
        "change from EXP-022 is the provider invocation: the two-line prompt is delivered",
        "through a per-record `--prompt-file` instead of an inline `--single=<prompt>` argv",
        "element, which the Windows `grok.CMD` shim truncates at the embedded newline.",
        "",
        f"Pool fingerprint: `{results['source_fingerprint']}`; blind record-ID fingerprint: `{results['blind_record_ids_fingerprint']}`.",
        "",
        "| Partition | Arm | Requested model | Surfaced IDs | Resolved | Coverage | Accuracy | Wilson 95% | Statuses |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for label in ("public_selection", "blind_holdout"):
        partition = results[label]
        for arm_id, arm in partition["arms"].items():
            surfaced = ", ".join(arm.get("surfaced_model_ids") or []) or "(none)"
            lines.append(
                f"| `{label}` | `{arm_id}` | `{arm.get('requested_model')}` | `{surfaced}` | "
                f"{arm.get('resolved_count')}/{arm.get('record_count')} | "
                f"{_fmt(arm.get('resolved_coverage'))} | {_fmt(arm.get('accuracy'))} | "
                f"`{_interval(arm.get('accuracy_wilson_95'))}` | `{arm.get('status_counts')}` |"
            )
    lines.extend(
        [
            "",
            "Provider failures, rate limits, timeouts, and parse ambiguity remain unresolved and",
            "receive no fallback label. The blind holdout was not used to select anything.",
            "",
            "See `README.md` for the root cause and the pre-run canary evidence.",
        ]
    )
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "experiment_id": EXPERIMENT_ID,
        "public": {
            arm: view["status_counts"] for arm, view in results["public_selection"]["arms"].items()
        },
        "blind": {
            arm: view["status_counts"] for arm, view in results["blind_holdout"]["arms"].items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--blind", type=Path, required=True)
    parser.add_argument("--code-commit", default="pending")
    args = parser.parse_args()
    print(
        json.dumps(
            finalize(
                output=args.output,
                public=args.public,
                blind=args.blind,
                code_commit=args.code_commit,
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
