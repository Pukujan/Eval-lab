"""Write the EXP-033 public report: per-task gold baselines, no model scoring.

Reads the frozen ``canonical-records.jsonl`` and states, per subtask, the row
and split counts, the gold label distribution, and the majority-label baseline
(an exact tie is reported as a tie). This is a gold-only summary: it makes no
model calls and writes no ``results.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from eval_lab.datasets.legalbench import SUBTASK_NAMES, label_distribution, majority_baseline

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = ROOT / "experiments" / "EXP-20261006-033-legalbench-answer-key-subset"
CANONICAL_PATH = EXPERIMENT_DIR / "canonical-records.jsonl"
REPORT_PATH = EXPERIMENT_DIR / "report.md"


def _load_records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def build_report(records: list[dict]) -> str:
    by_task: dict[str, list[dict]] = {task: [] for task in SUBTASK_NAMES}
    for record in records:
        task = record["gold"]["evidence"]["task"]
        by_task.setdefault(task, []).append(record)

    lines = [
        "# EXP-033 — LegalBench answer-key subset (public report)",
        "",
        (
            "This report is gold-only: it summarizes the frozen answer-key subset and "
            "states each task's majority-label baseline. No model has been scored, so "
            "there is no `results.json` and no accuracy claim about any judge."
        ),
        "",
        (
            "The subset is three binary answer-key tasks. It is a wider legal axis than "
            "Hearsay alone, not a general legal-reasoning score."
        ),
        "",
        "## Per-task baselines",
        "",
        "| task | records | public | blind | Yes | No | majority | baseline accuracy |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for task in SUBTASK_NAMES:
        task_records = by_task.get(task, [])
        split_counts = Counter(record["split"] for record in task_records)
        labels = [record["gold"]["label"] for record in task_records]
        counts = label_distribution(labels)
        baseline = majority_baseline(labels)
        majority = baseline["label"]
        if baseline["tie"]:
            majority = f"{majority} (tie)"
        lines.append(
            f"| `{task}` | {len(task_records)} | {split_counts.get('calibration', 0)} "
            f"| {split_counts.get('test', 0)} | {counts.get('Yes', 0)} | {counts.get('No', 0)} "
            f"| {majority} | {baseline['accuracy']:.4f} |"
        )
    lines += [
        "",
        (
            "`public` and `blind` are the calibration and test partitions of the "
            "case-disjoint split. The baseline is the accuracy of always predicting the "
            "majority gold label across all of a task's records; a tie is shown as a tie "
            "rather than an arbitrary pick."
        ),
        "",
        "## Interpretation limits",
        "",
        (
            "- Gold is the pinned LegalBench answer key (`answer_key` provenance). No "
            "model judgment is promoted to gold."
        ),
        (
            "- `citation_prediction_classification` repeats the same text with opposite "
            "answers (53 of its 54 distinct texts appear twice), so the case unit is the "
            "text and the case-disjoint split keeps every copy of a text on one side. Its "
            "majority label is an exact tie, so a majority baseline carries no signal."
        ),
        (
            "- Gold labels are native `Yes`/`No`; the shared single-mode path defaults to "
            '`pass`/`fail`, so scoring must use the `label_set ["Yes", "No"]` contract '
            "recorded in `typed-question-spec.json`."
        ),
        "- This is a frozen preregistration artifact; the blind partition is not scored.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", type=Path, default=CANONICAL_PATH)
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    args = parser.parse_args()
    if not args.canonical.is_file():
        print(f"missing canonical dataset: {args.canonical}", file=sys.stderr)
        return 1
    report = build_report(_load_records(args.canonical))
    args.output.write_text(report, encoding="utf-8", newline="\n")
    print(f"wrote {args.output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
