"""Consolidated accuracy/coverage analysis of every judge arm on the 760 blind records.

This is an offline re-analysis of committed prediction artifacts.  It makes no
model or provider calls.  Every number in ``paper/paper.md`` tables is produced
here and written between ``<!-- generated:NAME -->`` markers by ``--update-paper``.

Definitions (all on the frozen EXP-015 blind holdout, 760 records):

* resolved: the arm returned a legal label (``execution_status == "ok"``);
* coverage: resolved / 760;
* conditional accuracy: correct / resolved (what accuracy-only tables report);
* all-record accuracy: correct / 760 (an unresolved record earns no credit);
* Wilson: 95% Wilson score interval;
* paired tests: exact two-sided McNemar tests with Holm correction, computed on
  records resolved by both arms and, separately, on all 760 records with
  unresolved counted as not correct.

Usage:
    .venv\\Scripts\\python.exe scripts\\analyze_judge_comparison.py [--update-paper]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ID = "EXP-20260924-029-consolidated-judge-analysis"
OUT = ROOT / "experiments" / EXPERIMENT_ID
PAPER = ROOT / "paper" / "paper.md"
RECORDS = ROOT / "experiments" / "EXP-20260921-015-grok-luna-qwen-bakeoff" / "records.jsonl"
BLIND = "blind_holdout"
Z95 = 1.959963984540054


@dataclass(frozen=True)
class Arm:
    key: str
    label: str
    experiment: str
    family: str  # provider_api | local | baseline
    route: str
    harness: str
    paths: tuple[str, ...]  # later paths only fill records unresolved in earlier ones
    derived: bool = False


E = "experiments/"
ARMS: tuple[Arm, ...] = (
    Arm(
        "jev_exp014",
        "Jev 1.13 (EXP-014)",
        "EXP-014",
        "provider_api",
        "OpenRouter typesafe/jev-1.13 (pinned)",
        "Jev Decisions typed runner",
        (E + "EXP-20260921-014-independent-jev-benchmark/predictions-jev_pinned.jsonl",),
    ),
    Arm(
        "qwen_flash_exp013",
        "Qwen3.8 Flash, thinking off (EXP-013/014)",
        "EXP-013",
        "provider_api",
        "YOLO-Auto qwen3.8-flash",
        "run_qwen_streaming_retry._prompt: max_tokens=128, enable_thinking=False",
        (
            E
            + "EXP-20260921-013-qwen-multidomain-holdout/qwen-blind-merged-20260921/predictions.jsonl",
        ),
    ),
    Arm(
        "grok46_exp015",
        "Grok 4.6 Build (EXP-015)",
        "EXP-015",
        "provider_api",
        "xAI Grok Build CLI",
        "run_grok_luna_qwen_bakeoff typed packet",
        (
            E + "EXP-20260921-015-grok-luna-qwen-bakeoff/runs/blind-stream-parallel-20260921/"
            "predictions/grok.jsonl",
        ),
    ),
    Arm(
        "qwen_flash_exp015",
        "Qwen3.8 Flash, one pass (EXP-015)",
        "EXP-015",
        "provider_api",
        "YOLO-Auto qwen3.8-flash",
        "run_grok_luna_qwen_bakeoff._qwen_payload: no max_tokens, no thinking flag",
        (
            E + "EXP-20260921-015-grok-luna-qwen-bakeoff/runs/blind-stream-parallel-20260921/"
            "predictions/qwen_flash.jsonl",
        ),
    ),
    Arm(
        "qwen_flash_exp015_016",
        "Qwen3.8 Flash, EXP-015 + EXP-016 retry (declared merge)",
        "EXP-015+016",
        "provider_api",
        "YOLO-Auto qwen3.8-flash",
        "as EXP-015; rate-limited records filled from the EXP-016 retry",
        (
            E + "EXP-20260921-015-grok-luna-qwen-bakeoff/runs/blind-stream-parallel-20260921/"
            "predictions/qwen_flash.jsonl",
            E
            + "EXP-20260921-016-qwen-rate-limit-retry/runs/retry-20260921/predictions/qwen_flash.jsonl",
        ),
        derived=True,
    ),
    Arm(
        "grok46_exp022",
        "Grok 4.6 Build (EXP-022)",
        "EXP-022",
        "provider_api",
        "xAI Grok Build CLI",
        "run_grok_luna_qwen_bakeoff typed packet",
        (
            E
            + "EXP-20260922-022-fast-provider-wave/runs/blind-grok-46-20260922/predictions/grok.jsonl",
        ),
    ),
    Arm(
        "grok47_exp022",
        "Grok 4.7 Build (EXP-022)",
        "EXP-022",
        "provider_api",
        "xAI Grok Build CLI",
        "run_grok_luna_qwen_bakeoff typed packet",
        (
            E + "EXP-20260922-022-fast-provider-wave/runs/blind-grok-47-20260922/predictions/"
            "grok_47.jsonl",
        ),
    ),
    Arm(
        "qwen_flash_exp022",
        "Qwen3.8 Flash (EXP-022)",
        "EXP-022",
        "provider_api",
        "YOLO-Auto qwen3.8-flash",
        "run_grok_luna_qwen_bakeoff._qwen_payload: no max_tokens, no thinking flag",
        (
            E + "EXP-20260922-022-fast-provider-wave/runs/blind-qwen-flash-20260922/predictions/"
            "qwen_flash.jsonl",
        ),
    ),
    Arm(
        "jev_exp022",
        "Jev 1.13 (EXP-022)",
        "EXP-022",
        "provider_api",
        "OpenRouter typesafe/jev-1.13",
        "Jev Decisions typed runner",
        (E + "EXP-20260922-022-fast-provider-wave/runs/blind-jev-20260922/predictions.jsonl",),
    ),
    *(
        Arm(
            f"{key}_exp024",
            f"{label} (EXP-024)",
            "EXP-024",
            "provider_api",
            f"InferHub {route}",
            "run_inferhub_arm.build_prompt: user-only prompt, max_tokens=1024",
            (
                E + f"EXP-20260922-024-inferhub-recommendation-wave/runs/blind-{key}-20260922/"
                "predictions.jsonl",
            ),
        )
        for key, label, route in (
            ("ali_qwen38_flash", "Qwen3.8 Flash", "ali/qwen3.8-flash"),
            ("ali_qwen38_max", "Qwen 3.8 Max", "ali/qwen3.8-max"),
            ("ali_glm52", "GLM 5.2", "ali/glm-5.2"),
            ("ali_kimi_k27_code", "Kimi K2.7 Code", "ali/kimi-k2.7-code"),
            ("cbcn_deepseek_v4_flash", "DeepSeek V4 Flash", "cbcn/deepseek-v4-flash"),
            ("cb_deepseek_v41_flash", "DeepSeek V4.1 Flash", "cb/deepseek-v4.1-flash"),
            ("cbcn_glm53_flash", "GLM 5.3 Flash", "cbcn/glm-5.3-flash"),
            ("cbcn_minimax_m3", "MiniMax M3", "cbcn/minimax-m3"),
        )
    ),
    Arm(
        "grok46_exp025",
        "Grok 4.6 Build, typed rerun (EXP-025)",
        "EXP-025",
        "provider_api",
        "xAI Grok Build CLI",
        "run_grok_protocol_ablation typed_schema variant",
        (
            E + "EXP-20260922-025-grok-protocol-ablation/runs/blind-typed-baseline-20260922/"
            "grok_46-typed_schema/predictions.jsonl",
        ),
    ),
    Arm(
        "qwen3_4b_exp017",
        "Qwen3-4B local forced choice (EXP-017)",
        "EXP-017",
        "local",
        "local transformers, CUDA",
        "label log-likelihood scorer, 2,048-token cap",
        (
            E + "EXP-20260921-017-judge-calibration/runs/blind-qwen4b-4bit-20260921/"
            "raw_predictions.jsonl",
        ),
    ),
    *(
        Arm(
            f"{key.replace('-', '_').replace('.', '')}_exp027",
            f"{label} (EXP-027)",
            "EXP-027",
            "local",
            "local, Apple M1 16 GiB",
            f"native legal-label scoring, {cap}-token cap",
            (
                E
                + f"EXP-20260924-027-local-decision-bakeoff/blind-predictions/{key}/predictions.jsonl",
            ),
        )
        for key, label, cap in (
            ("kev-4b", "Kev-4B", "1,024"),
            ("semif-qwen35-4b", "SemIf (Qwen3.5-4B)", "4,096"),
            ("verdict-1.4", "Verdict 1.4", "512"),
            ("verdict-original", "Verdict pre-v1.4", "1,024"),
            ("kev-0.8b", "Kev-0.8B", "1,024"),
            ("laya-421m", "Laya 421M", "512"),
        )
    ),
    Arm(
        "majority_exp014",
        "Majority label (EXP-014 reference)",
        "EXP-014",
        "baseline",
        "none",
        "most frequent public-selection label per mode",
        (E + "EXP-20260921-014-independent-jev-benchmark/predictions-majority_baseline.jsonl",),
    ),
)

# Arms whose pairwise differences the paper discusses.  Holm correction is applied
# over every pair in ``ARMS`` regardless; this list only selects rows for tables.
FOCUS_PAIRS: tuple[tuple[str, str], ...] = (
    ("ali_qwen38_flash_exp024", "ali_qwen38_max_exp024"),
    ("ali_qwen38_flash_exp024", "cbcn_deepseek_v4_flash_exp024"),
    ("ali_qwen38_flash_exp024", "ali_glm52_exp024"),
    ("qwen_flash_exp022", "jev_exp022"),
    ("qwen_flash_exp022", "ali_qwen38_flash_exp024"),
    ("qwen_flash_exp013", "qwen_flash_exp022"),
    ("jev_exp014", "jev_exp022"),
    ("jev_exp022", "kev_4b_exp027"),
    ("grok46_exp022", "grok47_exp022"),
    ("grok46_exp022", "grok46_exp025"),
    ("kev_4b_exp027", "semif_qwen35_4b_exp027"),
    ("kev_4b_exp027", "majority_exp014"),
    ("semif_qwen35_4b_exp027", "majority_exp014"),
    ("grok46_exp022", "majority_exp014"),
    ("verdict_14_exp027", "majority_exp014"),
)

SOURCE_GROUPS = {
    "allenai/ai2_arc:ARC-Easy": "ARC-Easy (pairwise)",
    "eval-lab-select-v0.1.0": "EvalLab-Select / ARC-Challenge",
    "openai/gsm8k:main": "GSM8K",
}


def source_group(dataset: str) -> str:
    if dataset.startswith("cais/mmlu:"):
        return "MMLU (8 subjects)"
    if dataset.startswith("eval-lab-synthetic:"):
        return "Eval Lab synthetic (4 families)"
    return SOURCE_GROUPS[dataset]


def wilson(successes: int, trials: int) -> list[float] | None:
    if trials == 0:
        return None
    p = successes / trials
    denom = 1 + Z95**2 / trials
    centre = (p + Z95**2 / (2 * trials)) / denom
    half = Z95 * math.sqrt(p * (1 - p) / trials + Z95**2 / (4 * trials**2)) / denom
    return [max(0.0, centre - half), min(1.0, centre + half)]


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from the discordant counts b and c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def holm(pvalues: dict[str, float]) -> dict[str, float]:
    ordered = sorted(pvalues.items(), key=lambda item: (item[1], item[0]))
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (key, value) in enumerate(ordered):
        running = max(running, min(1.0, (m - rank) * value))
        adjusted[key] = running
    return adjusted


def sha256(path: Path) -> str:
    """SHA-256 of the LF-normalized bytes, so Windows CRLF checkouts hash identically."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_blind_records() -> dict[str, dict[str, Any]]:
    records = {}
    for row in load_jsonl(RECORDS):
        if row["partition"] != BLIND:
            continue
        record = row["record"]
        records[record["record_id"]] = {
            "gold": record["gold"]["label"],
            "mode": record["mode"],
            "dataset": row["dataset"],
            "source": source_group(row["dataset"]),
        }
    return records


def unresolved_reason(prediction: dict[str, Any]) -> str:
    status = prediction["execution_status"]
    error = prediction.get("error")
    kind = error.get("kind") if isinstance(error, dict) else None
    if status == "skipped" and kind == "abstention":
        return "abstention"
    if status == "skipped" and kind == "context_limit":
        return "context_limit_skip"
    if status == "provider_error" and (kind == "timeout" or error == "timeout"):
        return "provider_timeout"
    if status == "provider_error":
        return "provider_error"
    return str(status)


def load_arm(arm: Arm, records: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for rel in arm.paths:
        for row in load_jsonl(ROOT / rel):
            prediction = row.get("prediction", row)
            record_id = prediction["record_id"]
            if record_id not in records:
                raise ValueError(f"{arm.key}: {record_id} is not a blind record")
            previous = merged.get(record_id)
            if previous is None or previous["execution_status"] != "ok":
                merged[record_id] = prediction
    if set(merged) != set(records):
        raise ValueError(f"{arm.key}: predictions do not cover the 760 blind records")
    return merged


def summarize(
    arm: Arm, predictions: dict[str, dict[str, Any]], records: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    total = len(records)
    statuses: Counter[str] = Counter()
    correct = 0
    resolved = 0
    by_mode: dict[str, list[int]] = {}
    by_source: dict[str, list[int]] = {}
    latencies = []
    completion_tokens = []
    for record_id, record in records.items():
        prediction = predictions[record_id]
        ok = prediction["execution_status"] == "ok" and prediction.get("label") is not None
        statuses["ok" if ok else unresolved_reason(prediction)] += 1
        latency = prediction.get("latency_ms")
        if ok and isinstance(latency, (int, float)):
            latencies.append(float(latency))
        usage = prediction.get("token_usage")
        if ok and isinstance(usage, dict) and isinstance(usage.get("completion_tokens"), int):
            completion_tokens.append(usage["completion_tokens"])
        for bucket, key in ((by_mode, record["mode"]), (by_source, record["source"])):
            cell = bucket.setdefault(key, [0, 0, 0])
            cell[2] += 1
            if ok:
                cell[1] += 1
                cell[0] += int(prediction["label"] == record["gold"])
        if ok:
            resolved += 1
            correct += int(prediction["label"] == record["gold"])

    def cells(bucket: dict[str, list[int]]) -> dict[str, Any]:
        return {
            key: {
                "records": value[2],
                "resolved": value[1],
                "correct": value[0],
                "accuracy": value[0] / value[1] if value[1] else None,
                "accuracy_95_wilson": wilson(value[0], value[1]),
            }
            for key, value in sorted(bucket.items())
        }

    return {
        "label": arm.label,
        "experiment": arm.experiment,
        "family": arm.family,
        "route": arm.route,
        "harness": arm.harness,
        "derived": arm.derived,
        "sources": [{"path": rel, "sha256": sha256(ROOT / rel)} for rel in arm.paths],
        "record_count": total,
        "resolved": resolved,
        "correct": correct,
        "coverage": resolved / total,
        "coverage_95_wilson": wilson(resolved, total),
        "conditional_accuracy": correct / resolved if resolved else None,
        "conditional_accuracy_95_wilson": wilson(correct, resolved),
        "all_record_accuracy": correct / total,
        "all_record_accuracy_95_wilson": wilson(correct, total),
        "status_counts": dict(sorted(statuses.items())),
        "by_mode": cells(by_mode),
        "by_source": cells(by_source),
        "median_resolved_latency_ms": statistics.median(latencies) if latencies else None,
        "median_resolved_completion_tokens": (
            statistics.median(completion_tokens) if completion_tokens else None
        ),
    }


def paired_tests(
    predictions: dict[str, dict[str, dict[str, Any]]], records: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    raw_shared: dict[str, float] = {}
    raw_all: dict[str, float] = {}
    rows: dict[str, dict[str, Any]] = {}
    for left, right in combinations([arm.key for arm in ARMS], 2):
        key = f"{left}|{right}"
        shared = b = c = 0
        b_all = c_all = 0
        for record_id, record in records.items():
            lp, rp = predictions[left][record_id], predictions[right][record_id]
            l_ok = lp["execution_status"] == "ok" and lp.get("label") is not None
            r_ok = rp["execution_status"] == "ok" and rp.get("label") is not None
            l_hit = l_ok and lp["label"] == record["gold"]
            r_hit = r_ok and rp["label"] == record["gold"]
            if l_hit and not r_hit:
                b_all += 1
            elif r_hit and not l_hit:
                c_all += 1
            if l_ok and r_ok:
                shared += 1
                if l_hit and not r_hit:
                    b += 1
                elif r_hit and not l_hit:
                    c += 1
        raw_shared[key] = mcnemar_exact(b, c)
        raw_all[key] = mcnemar_exact(b_all, c_all)
        rows[key] = {
            "left": left,
            "right": right,
            "shared_resolved": shared,
            "shared_left_only_correct": b,
            "shared_right_only_correct": c,
            "shared_p_exact": raw_shared[key],
            "all_left_only_correct": b_all,
            "all_right_only_correct": c_all,
            "all_p_exact": raw_all[key],
        }
    adj_shared = holm(raw_shared)
    adj_all = holm(raw_all)
    for key, row in rows.items():
        row["shared_p_holm"] = adj_shared[key]
        row["all_p_holm"] = adj_all[key]
    return {
        "method": "exact two-sided McNemar; Holm correction over all "
        f"{len(rows)} arm pairs, separately for each view",
        "pairs": rows,
    }


GROK_ABLATION = E + "EXP-20260922-025-grok-protocol-ablation/results.json"


def grok_ablation_summary() -> dict[str, Any]:
    """Public-diagnostic variant scores from EXP-025, copied for the paper appendix table."""
    path = ROOT / GROK_ABLATION
    payload = json.loads(path.read_text(encoding="utf-8"))
    public = payload["public"]
    return {
        "path": GROK_ABLATION,
        "sha256": sha256(path),
        "public_record_count": public["record_count"],
        "variants": {key: public["variants"][key] for key in sorted(public["variants"])},
    }


def build() -> dict[str, Any]:
    records = load_blind_records()
    if len(records) != 760:
        raise ValueError(f"expected 760 blind records, found {len(records)}")
    predictions = {arm.key: load_arm(arm, records) for arm in ARMS}
    arms = {arm.key: summarize(arm, predictions[arm.key], records) for arm in ARMS}
    composition: dict[str, Counter[str]] = {}
    for record in records.values():
        composition.setdefault(record["source"], Counter())[record["mode"]] += 1
    gold = Counter((record["mode"], record["gold"]) for record in records.values())
    order_conditional = sorted(
        (k for k in arms if arms[k]["family"] != "baseline"),
        key=lambda k: (-(arms[k]["conditional_accuracy"] or 0), k),
    )
    order_all = sorted(
        (k for k in arms if arms[k]["family"] != "baseline"),
        key=lambda k: (-arms[k]["all_record_accuracy"], k),
    )
    return {
        "experiment_id": EXPERIMENT_ID,
        "status": "completed",
        "analysis": "offline re-analysis of committed blind predictions; no model calls",
        "grok_protocol_ablation": grok_ablation_summary(),
        "records": {
            "path": str(RECORDS.relative_to(ROOT).as_posix()),
            "sha256": sha256(RECORDS),
            "blind_count": len(records),
            "composition": {
                source: dict(sorted(modes.items())) for source, modes in sorted(composition.items())
            },
            "gold_by_mode": {f"{mode}:{label}": n for (mode, label), n in sorted(gold.items())},
        },
        "definitions": {
            "coverage": "resolved / 760",
            "conditional_accuracy": "correct / resolved",
            "all_record_accuracy": "correct / 760; unresolved earns no credit",
            "interval": "95% Wilson score interval",
        },
        "arms": arms,
        "rank_by_conditional_accuracy": order_conditional,
        "rank_by_all_record_accuracy": order_all,
        "paired_tests": paired_tests(predictions, records),
        "focus_pairs": [f"{a}|{b}" for a, b in FOCUS_PAIRS],
        "not_run": {
            "mimo_v25_exp024": "cp/cline-pass/mimo-v2.5 returned HTTP 402 on both canary attempts; "
            "no blind predictions exist (EXP-024 RESULTS.md)",
            "bespoke_nimble_9b_exp027": "pinned unquantized configuration does not fit the 16 GiB host",
            "kev_9b_exp027": "pinned configuration does not fit the 16 GiB host",
        },
        "excluded": {
            "luna_exp015": "vendor-independent orchestrator comparison policy (EXP-019)",
        },
    }


# ---------------------------------------------------------------- rendering


def pct(value: float | None, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value * 100:.{digits}f}%"


def interval(values: list[float] | None) -> str:
    return "n/a" if values is None else f"{values[0] * 100:.1f}–{values[1] * 100:.1f}"


def pval(value: float) -> str:
    if value < 0.0001:
        return "<0.0001"
    return f"{value:.4f}"


STATUS_ORDER = (
    "rate_limited",
    "provider_error",
    "provider_timeout",
    "parse_error",
    "abstention",
    "context_limit_skip",
)
STATUS_LABELS = {
    "rate_limited": "rate limited (429)",
    "provider_error": "provider error",
    "provider_timeout": "provider timeout",
    "parse_error": "parse failure",
    "abstention": "abstention",
    "context_limit_skip": "context-cap skip",
}


def table_main(result: dict[str, Any]) -> str:
    arms = result["arms"]
    lines = [
        (
            "| Arm | Family | Resolved | Coverage | Conditional accuracy (95% CI) | "
            "All-record accuracy (95% CI) | Unresolved |"
        ),
        "|---|---|---:|---:|---:|---:|---|",
    ]
    order = result["rank_by_all_record_accuracy"] + [
        k for k in arms if arms[k]["family"] == "baseline"
    ]
    for key in order:
        arm = arms[key]
        unresolved = ", ".join(
            f"{STATUS_LABELS[s]} {arm['status_counts'][s]}"
            for s in STATUS_ORDER
            if arm["status_counts"].get(s)
        )
        family = {"provider_api": "API", "local": "local", "baseline": "reference"}[arm["family"]]
        lines.append(
            f"| {arm['label']} | {family} | {arm['resolved']}/{arm['record_count']} | "
            f"{pct(arm['coverage'])} | {pct(arm['conditional_accuracy'])} "
            f"({interval(arm['conditional_accuracy_95_wilson'])}) | "
            f"{pct(arm['all_record_accuracy'])} ({interval(arm['all_record_accuracy_95_wilson'])}) | "
            f"{unresolved or '—'} |"
        )
    return "\n".join(lines)


def table_ranks(result: dict[str, Any]) -> str:
    arms = result["arms"]
    cond = result["rank_by_conditional_accuracy"]
    allr = result["rank_by_all_record_accuracy"]
    lines = [
        "| Arm | Rank by conditional accuracy | Rank by all-record accuracy | Shift |",
        "|---|---:|---:|---:|",
    ]
    for key in cond:
        a, b = cond.index(key) + 1, allr.index(key) + 1
        if a != b:
            lines.append(f"| {arms[key]['label']} | {a} | {b} | {a - b:+d} |")
    return "\n".join(lines)


def table_pairs(result: dict[str, Any]) -> str:
    arms = result["arms"]
    pairs = result["paired_tests"]["pairs"]
    lines = [
        (
            "| Comparison (A vs B) | Shared resolved | A-only / B-only correct | Holm p (shared) | "
            "A-only / B-only correct, all 760 | Holm p (all 760) |"
        ),
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key in result["focus_pairs"]:
        row = pairs[key]
        lines.append(
            f"| {arms[row['left']]['label']} vs {arms[row['right']]['label']} | "
            f"{row['shared_resolved']} | {row['shared_left_only_correct']} / "
            f"{row['shared_right_only_correct']} | {pval(row['shared_p_holm'])} | "
            f"{row['all_left_only_correct']} / {row['all_right_only_correct']} | "
            f"{pval(row['all_p_holm'])} |"
        )
    return "\n".join(lines)


SOURCE_ARMS = (
    "qwen_flash_exp013",
    "qwen_flash_exp022",
    "ali_qwen38_flash_exp024",
    "jev_exp022",
    "grok46_exp022",
    "kev_4b_exp027",
)


def table_sources(result: dict[str, Any]) -> str:
    arms = result["arms"]
    comp = result["records"]["composition"]
    sources = list(comp)
    lines = [
        "| Source (blind records) | " + " | ".join(arms[k]["label"] for k in SOURCE_ARMS) + " |",
        "|---|" + "---:|" * len(SOURCE_ARMS),
    ]
    for source in sources:
        n = sum(comp[source].values())
        cells = []
        for key in SOURCE_ARMS:
            cell = arms[key]["by_source"][source]
            cells.append(f"{pct(cell['accuracy'], 1)} ({cell['correct']}/{cell['resolved']})")
        lines.append(f"| {source} ({n}) | " + " | ".join(cells) + " |")
    return "\n".join(lines)


QWEN_ARMS = (
    "qwen_flash_exp013",
    "qwen_flash_exp015",
    "qwen_flash_exp015_016",
    "qwen_flash_exp022",
    "ali_qwen38_flash_exp024",
)


def table_qwen(result: dict[str, Any]) -> str:
    arms = result["arms"]
    lines = [
        (
            "| Run | Request configuration | Median latency (resolved) | Coverage | Conditional accuracy | "
            "GSM8K accuracy |"
        ),
        "|---|---|---:|---:|---:|---:|",
    ]
    for key in QWEN_ARMS:
        arm = arms[key]
        gsm = arm["by_source"]["GSM8K"]
        lines.append(
            f"| {arm['label']} | {arm['harness']} | {arm['median_resolved_latency_ms'] / 1000:.2f} s | "
            f"{pct(arm['coverage'])} | {pct(arm['conditional_accuracy'])} | "
            f"{pct(gsm['accuracy'], 1)} ({gsm['correct']}/{gsm['resolved']}) |"
        )
    return "\n".join(lines)


def table_modes(result: dict[str, Any]) -> str:
    arms = result["arms"]
    lines = [
        "| Arm | Single pass/fail accuracy | Pairwise A/B/TIE accuracy |",
        "|---|---:|---:|",
    ]
    for key in result["rank_by_all_record_accuracy"]:
        arm = arms[key]
        s, p = arm["by_mode"]["single"], arm["by_mode"]["pairwise"]
        lines.append(
            f"| {arm['label']} | {pct(s['accuracy'])} ({s['correct']}/{s['resolved']}) | "
            f"{pct(p['accuracy'])} ({p['correct']}/{p['resolved']}) |"
        )
    return "\n".join(lines)


def table_composition(result: dict[str, Any]) -> str:
    comp = result["records"]["composition"]
    lines = ["| Source | Single | Pairwise | Total |", "|---|---:|---:|---:|"]
    for source, modes in comp.items():
        s, p = modes.get("single", 0), modes.get("pairwise", 0)
        lines.append(f"| {source} | {s} | {p} | {s + p} |")
    s = sum(m.get("single", 0) for m in comp.values())
    p = sum(m.get("pairwise", 0) for m in comp.values())
    lines.append(f"| **Total** | {s} | {p} | {s + p} |")
    return "\n".join(lines)


# --- Slim body tables (plain labels, 1-decimal percentages) -----------------

PLAIN = {
    "ali_qwen38_flash_exp024": "Qwen3.8 Flash",
    "ali_qwen38_max_exp024": "Qwen 3.8 Max",
    "ali_kimi_k27_code_exp024": "Kimi K2.7 Code",
    "jev_exp022": "Jev 1.13",
    "kev_4b_exp027": "Kev-4B (best local model)",
    "majority_exp014": "Always-same-answer baseline",
    "grok46_exp022": "Grok 4.6 Build",
    "cbcn_deepseek_v4_flash_exp024": "DeepSeek V4 Flash",
    "ali_glm52_exp024": "GLM 5.2",
    "qwen_flash_exp015": "Qwen3.8 Flash, one pass",
    "verdict_14_exp027": "Verdict 1.4 (local)",
    "verdict_original_exp027": "Verdict pre-v1.4 (local)",
    "semif_qwen35_4b_exp027": "SemIf 4B",
    "kev_08b_exp027": "Kev-0.8B",
    "laya_421m_exp027": "Laya 421M",
    "qwen3_4b_exp017": "Qwen3-4B",
}
BODY_LEADERS = (
    "ali_qwen38_flash_exp024",
    "ali_qwen38_max_exp024",
    "ali_kimi_k27_code_exp024",
    "jev_exp022",
    "kev_4b_exp027",
    "majority_exp014",
    "grok46_exp022",
)
BODY_HIDDEN = (
    "cbcn_deepseek_v4_flash_exp024",
    "ali_glm52_exp024",
    "qwen_flash_exp015",
    "verdict_14_exp027",
    "verdict_original_exp027",
)
BODY_LOCAL = (
    "kev_4b_exp027",
    "semif_qwen35_4b_exp027",
    "kev_08b_exp027",
    "laya_421m_exp027",
    "qwen3_4b_exp017",
    "verdict_14_exp027",
    "verdict_original_exp027",
    "majority_exp014",
)
QWEN_SETTINGS = {
    "qwen_flash_exp013": ("EXP-013", "128-token cap, thinking off"),
    "qwen_flash_exp022": ("EXP-022", "provider defaults"),
    "ali_qwen38_flash_exp024": ("EXP-024", "other route and prompt, 1,024-token cap"),
}
STATUS_PLAIN = {
    "rate_limited": "rate-limited",
    "provider_error": "provider errors",
    "provider_timeout": "timeouts",
    "parse_error": "unreadable answers",
    "abstention": "abstained",
    "context_limit_skip": "too long for the model",
}


def p1(value: float | None) -> str:
    return pct(value, 1)


def lost_reason(arm: dict[str, Any]) -> str:
    parts = [
        f"{arm['status_counts'][s]} {STATUS_PLAIN[s]}"
        for s in STATUS_ORDER
        if arm["status_counts"].get(s, 0) >= 5
    ]
    return ", ".join(parts) or "—"


def table_body_leaders(result: dict[str, Any]) -> str:
    arms = result["arms"]
    lines = [
        "| Judge | Type | Answered | Correct, all 760 questions |",
        "|---|---|---:|---:|",
    ]
    for key in BODY_LEADERS:
        arm = arms[key]
        kind = {"provider_api": "API", "local": "local", "baseline": "reference"}[arm["family"]]
        lines.append(
            f"| {PLAIN[key]} | {kind} | {p1(arm['coverage'])} | {p1(arm['all_record_accuracy'])} |"
        )
    return "\n".join(lines)


def table_body_hidden(result: dict[str, Any]) -> str:
    arms = result["arms"]
    lines = [
        "| Judge | Answered | Correct when it answered | Correct, all 760 | Why questions were lost |",
        "|---|---:|---:|---:|---|",
    ]
    for key in BODY_HIDDEN:
        arm = arms[key]
        lines.append(
            f"| {PLAIN[key]} | {p1(arm['coverage'])} | {p1(arm['conditional_accuracy'])} | "
            f"{p1(arm['all_record_accuracy'])} | {lost_reason(arm)} |"
        )
    return "\n".join(lines)


def table_body_qwen(result: dict[str, Any]) -> str:
    arms = result["arms"]
    lines = [
        "| Qwen3.8 Flash run | Request settings | Typical answer time | Correct when it answered | Math (GSM8K) |",
        "|---|---|---:|---:|---:|",
    ]
    for key, (label, settings) in QWEN_SETTINGS.items():
        arm = arms[key]
        lines.append(
            f"| {label} | {settings} | {arm['median_resolved_latency_ms'] / 1000:.1f} s | "
            f"{p1(arm['conditional_accuracy'])} | {p1(arm['by_source']['GSM8K']['accuracy'])} |"
        )
    return "\n".join(lines)


def table_body_local(result: dict[str, Any]) -> str:
    arms = result["arms"]
    lines = ["| Model | Answered | Correct, all 760 |", "|---|---:|---:|"]
    for key in BODY_LOCAL:
        arm = arms[key]
        lines.append(f"| {PLAIN[key]} | {p1(arm['coverage'])} | {p1(arm['all_record_accuracy'])} |")
    return "\n".join(lines)


SOURCE_BLURBS = {
    "MMLU (8 subjects)": ("MMLU (8 subjects)", "school and professional knowledge"),
    "GSM8K": ("GSM8K", "grade-school math word problems"),
    "EvalLab-Select / ARC-Challenge": ("ARC-Challenge", "harder science questions"),
    "ARC-Easy (pairwise)": ("ARC-Easy", "pick the better of two answers"),
    "Eval Lab synthetic (4 families)": ("Eval Lab synthetic", "small hand-built checks"),
}


def table_body_sources(result: dict[str, Any]) -> str:
    comp = result["records"]["composition"]
    rows = sorted(comp.items(), key=lambda item: (-sum(item[1].values()), item[0]))
    lines = ["| Source | Questions | What it tests |", "|---|---:|---|"]
    for source, modes in rows:
        name, blurb = SOURCE_BLURBS[source]
        lines.append(f"| {name} | {sum(modes.values())} | {blurb} |")
    return "\n".join(lines)


GROK_VARIANTS = (
    ("typed_schema", "typed schema (baseline)"),
    ("explicit_schema", "explicit wording + schema"),
    ("semantic_schema", "semantic labels + schema"),
    ("explicit_no_schema", "explicit wording, no schema"),
)


def table_grok_ablation(result: dict[str, Any]) -> str:
    ablation = result["grok_protocol_ablation"]
    n = ablation["public_record_count"]
    lines = ["| Request format | Public answered | Mode-balanced score |", "|---|---:|---:|"]
    for key, label in GROK_VARIANTS:
        variant = ablation["variants"][key]
        score = variant["selection_score"]
        shown = "n/a (no readable answers)" if score is None else f"{score:.4f}"
        lines.append(f"| {label} | {variant['resolved']}/{n} | {shown} |")
    return "\n".join(lines)


TABLES = {
    "composition": table_composition,
    "main": table_main,
    "ranks": table_ranks,
    "pairs": table_pairs,
    "qwen": table_qwen,
    "sources": table_sources,
    "modes": table_modes,
    "body_leaders": table_body_leaders,
    "body_hidden": table_body_hidden,
    "body_qwen": table_body_qwen,
    "body_local": table_body_local,
    "body_sources": table_body_sources,
    "grok_ablation": table_grok_ablation,
}


def render_report(result: dict[str, Any]) -> str:
    parts = [
        f"# {EXPERIMENT_ID} — consolidated judge analysis",
        "",
        (
            "Offline re-analysis of committed blind predictions (760 records, frozen EXP-015 pool). "
            "No model or provider calls. Generated by `scripts/analyze_judge_comparison.py`."
        ),
        "",
    ]
    titles = {
        "composition": "Blind pool composition",
        "main": "All arms: coverage, conditional and all-record accuracy",
        "ranks": "Rank changes when unresolved records earn no credit",
        "pairs": "Paired exact McNemar tests (focus pairs; Holm over all pairs)",
        "qwen": "Qwen3.8 Flash across runs",
        "sources": "Per-source accuracy (same pool)",
        "modes": "Accuracy by decision mode",
        "body_leaders": "Paper body: leading and notable judges",
        "body_hidden": "Paper body: where accuracy-only numbers mislead",
        "body_qwen": "Paper body: Qwen3.8 Flash request settings",
        "body_local": "Paper body: local models",
        "body_sources": "Paper body: question sources",
        "grok_ablation": "EXP-025 Grok protocol ablation (public diagnostic)",
    }
    for name, render in TABLES.items():
        parts += [f"## {titles[name]}", "", render(result), ""]
    parts += [
        "## Not run or excluded",
        "",
        *[f"- `{k}`: {v}" for k, v in result["not_run"].items()],
        *[f"- `{k}`: {v}" for k, v in result["excluded"].items()],
        "",
    ]
    return "\n".join(parts)


MARKER = re.compile(
    r"<!-- generated:(?P<name>[a-z_]+) -->\n(?P<body>(?:(?!<!-- ).*\n)*?)<!-- /generated -->"
)


def _block(name: str, result: dict[str, Any]) -> str:
    return f"<!-- generated:{name} -->\n{TABLES[name](result)}\n<!-- /generated -->"


def update_paper(result: dict[str, Any], path: Path = PAPER) -> bool:
    text = path.read_text(encoding="utf-8")
    updated = MARKER.sub(lambda match: _block(match.group("name"), result), text)
    if updated != text:
        path.write_text(updated, encoding="utf-8", newline="\n")
    return updated != text


def paper_tables_current(result: dict[str, Any], path: Path = PAPER) -> bool:
    text = path.read_text(encoding="utf-8")
    matches = list(MARKER.finditer(text))
    return bool(matches) and all(
        match.group(0) == _block(match.group("name"), result) for match in matches
    )


def write_outputs(result: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "results.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    (OUT / "report.md").write_text(render_report(result), encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--update-paper", action="store_true")
    args = parser.parse_args()
    result = build()
    write_outputs(result)
    if args.update_paper:
        update_paper(result)
    print(f"wrote {OUT.relative_to(ROOT)}; {len(result['arms'])} arms")


if __name__ == "__main__":
    main()
