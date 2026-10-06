"""Canonicalize fixed-label LegalBench tasks: Hearsay and the answer-key subset.

Hearsay keeps its original single-task canonicalizer. The answer-key subset
adds ``overruling``, ``definition_classification``, and
``citation_prediction_classification`` through ``canonicalize_subtask_rows``.
Gold is always the LegalBench answer key (``GoldProvenance.ANSWER_KEY``); no
model judgment is promoted to gold. The split unit is the case: every row that
shares a normalized ``text`` maps to the same ``source_problem_id`` and the
same split, so no case crosses the calibration/test boundary. This matters for
``citation_prediction_classification``, whose test rows repeat the same text
with opposite answers.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from eval_lab.schema import (
    GoldLabel,
    GoldProvenance,
    JudgeRecord,
    JudgmentMode,
    RubricCriterion,
    Split,
)

HEARSAY_PROMPT_VERSION = "legalbench-hearsay-base-prompt-v1"
HEARSAY_RUBRIC = (
    "Decide whether the described evidence qualifies as hearsay under the "
    "definition in the prompt. Return Yes or No."
)
_REQUIRED_COLUMNS = {"index", "answer", "text", "slice"}


def canonicalize_hearsay_rows(
    rows: Sequence[Mapping[str, Any]], *, split: Split, prompt_template: str
) -> list[JudgeRecord]:
    """Convert task rows to fixed-choice judge records with source identities."""

    if prompt_template.count("{{text}}") != 1:
        raise ValueError("Hearsay prompt template must contain exactly one {{text}} slot")

    records: list[JudgeRecord] = []
    seen_indices: set[int] = set()
    for row in rows:
        missing = _REQUIRED_COLUMNS - row.keys()
        if missing:
            raise ValueError(f"Hearsay row is missing columns: {sorted(missing)}")
        try:
            source_index = int(row["index"])
        except (TypeError, ValueError) as exc:
            raise ValueError("Hearsay index must be an integer") from exc
        if source_index < 0 or source_index in seen_indices:
            raise ValueError(f"invalid or duplicate Hearsay row index: {source_index}")
        seen_indices.add(source_index)

        label = str(row["answer"]).strip()
        if label not in {"Yes", "No"}:
            raise ValueError(f"unsupported Hearsay answer label: {label!r}")
        text = str(row["text"]).strip()
        slice_name = str(row["slice"]).strip()
        if not text or not slice_name:
            raise ValueError("Hearsay text and slice must be non-empty")

        source_problem_id = f"legalbench-hearsay:{split.value}:{source_index}"
        records.append(
            JudgeRecord(
                record_id=source_problem_id,
                source_problem_id=source_problem_id,
                mode=JudgmentMode.SINGLE,
                prompt=prompt_template.replace("{{text}}", text),
                rubric=[
                    RubricCriterion(
                        criterion_id="legalbench-hearsay-classification",
                        description=HEARSAY_RUBRIC,
                        weight=1.0,
                        aggregation_rule="single_label",
                    )
                ],
                candidate_a=text,
                gold=GoldLabel(
                    label=label,
                    provenance=GoldProvenance.ANSWER_KEY,
                    evidence={"task": "hearsay", "slice": slice_name, "source_index": source_index},
                    verifier_id="legalbench-hearsay-answer-key-v1",
                ),
                split=split,
            )
        )
    return records


SUBTASK_NAMES: tuple[str, ...] = (
    "overruling",
    "definition_classification",
    "citation_prediction_classification",
)
_SUBTASK_LABELS = frozenset({"Yes", "No"})


@dataclass(frozen=True)
class _SubtaskSpec:
    """The fail-closed contract for one answer-key LegalBench subtask."""

    columns: frozenset[str]
    slots: tuple[str, ...]
    verifier_id: str
    prompt_version: str
    rubric: str


def _subtask_specs() -> dict[str, _SubtaskSpec]:
    common_rubric = "The candidate matches the LegalBench task answer key."
    return {
        "overruling": _SubtaskSpec(
            columns=frozenset({"index", "answer", "text"}),
            slots=("text",),
            verifier_id="legalbench-overruling-answer-key-v1",
            prompt_version="legalbench-overruling-base-prompt-v1",
            rubric=common_rubric,
        ),
        "definition_classification": _SubtaskSpec(
            columns=frozenset({"index", "text", "answer"}),
            slots=("text",),
            verifier_id="legalbench-definition-classification-answer-key-v1",
            prompt_version="legalbench-definition-classification-base-prompt-v1",
            rubric=common_rubric,
        ),
        "citation_prediction_classification": _SubtaskSpec(
            columns=frozenset({"index", "text", "citation", "answer"}),
            slots=("text", "citation"),
            verifier_id="legalbench-citation-prediction-classification-answer-key-v1",
            prompt_version="legalbench-citation-prediction-classification-base-prompt-v1",
            rubric=common_rubric,
        ),
    }


SUBTASK_SPECS: Mapping[str, _SubtaskSpec] = _subtask_specs()


def _normalize_text(text: str) -> str:
    return " ".join(text.split())


def _case_key(text: str) -> str:
    """Return the case identity shared by every row with the same text."""

    return hashlib.sha256(_normalize_text(text).encode("utf-8")).hexdigest()[:16]


def case_split(text: str, *, task: str, seed: int) -> Split:
    """Assign a case to calibration or test from its normalized text alone.

    Every row that shares a normalized ``text`` resolves to the same case key
    and therefore the same split, so no case crosses the boundary.
    """

    if task not in SUBTASK_SPECS:
        raise ValueError(f"unknown LegalBench subtask: {task!r}")
    payload = f"{seed}:legalbench-subset:{task}:{_case_key(text)}"
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    sample = int.from_bytes(digest[:8], byteorder="big") / float(2**64)
    return Split.CALIBRATION if sample < 0.5 else Split.TEST


def assign_case_splits(
    rows: Sequence[Mapping[str, Any]], *, task: str, seed: int
) -> list[tuple[Mapping[str, Any], Split]]:
    """Pair each row with its case split, failing closed on a missing text field."""

    paired: list[tuple[Mapping[str, Any], Split]] = []
    for row in rows:
        if "text" not in row:
            raise ValueError(f"{task} row is missing the text column")
        text = str(row["text"]).strip()
        if not text:
            raise ValueError(f"{task} text must be non-empty")
        paired.append((row, case_split(text, task=task, seed=seed)))
    return paired


def canonicalize_subtask_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    task: str,
    split: Split,
    prompt_template: str,
) -> list[JudgeRecord]:
    """Convert answer-key LegalBench subtask rows into single-choice records.

    The header contract is validated per task and fails closed on a mismatch:
    a missing or extra column, a missing or repeated prompt slot, a non-integer
    or duplicate index, an empty required field, or a label outside ``Yes`` /
    ``No`` all raise. ``source_problem_id`` is the case key, so rows sharing a
    text share one problem identity.
    """

    spec = SUBTASK_SPECS.get(task)
    if spec is None:
        raise ValueError(f"unknown LegalBench subtask: {task!r}")
    for slot in spec.slots:
        token = "{{" + slot + "}}"
        if prompt_template.count(token) != 1:
            raise ValueError(f"{task} prompt template must contain exactly one {token} slot")

    records: list[JudgeRecord] = []
    seen_indices: set[int] = set()
    for row in rows:
        present = set(row.keys())
        if present != spec.columns:
            missing = sorted(spec.columns - present)
            extra = sorted(present - spec.columns)
            raise ValueError(f"{task} row column mismatch: missing={missing} extra={extra}")
        try:
            source_index = int(row["index"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{task} index must be an integer") from exc
        if source_index < 0 or source_index in seen_indices:
            raise ValueError(f"invalid or duplicate {task} row index: {source_index}")
        seen_indices.add(source_index)

        label = str(row["answer"]).strip()
        if label not in _SUBTASK_LABELS:
            raise ValueError(f"unsupported {task} answer label: {label!r}")
        text = str(row["text"]).strip()
        if not text:
            raise ValueError(f"{task} text must be non-empty")

        prompt = prompt_template
        for slot in spec.slots:
            value = text if slot == "text" else str(row[slot]).strip()
            if not value:
                raise ValueError(f"{task} {slot} must be non-empty")
            prompt = prompt.replace("{{" + slot + "}}", value)

        evidence: dict[str, Any] = {
            "task": task,
            "source_index": source_index,
            "source_split": split.value,
        }
        if "citation" in spec.columns:
            evidence["citation"] = str(row["citation"]).strip()

        records.append(
            JudgeRecord(
                record_id=f"legalbench-{task}:{split.value}:{source_index}",
                source_problem_id=f"legalbench-{task}:case:{_case_key(text)}",
                mode=JudgmentMode.SINGLE,
                prompt=prompt,
                rubric=[
                    RubricCriterion(
                        criterion_id=f"legalbench-{task}-classification",
                        description=spec.rubric,
                        weight=1.0,
                        aggregation_rule="single_label",
                    )
                ],
                candidate_a=text,
                gold=GoldLabel(
                    label=label,
                    provenance=GoldProvenance.ANSWER_KEY,
                    evidence=evidence,
                    verifier_id=spec.verifier_id,
                ),
                split=split,
            )
        )
    return records


def label_distribution(labels: Sequence[str]) -> dict[str, int]:
    """Return the label counts in sorted label order."""

    return dict(sorted(Counter(labels).items()))


def majority_baseline(labels: Sequence[str]) -> dict[str, Any]:
    """Return the majority-label baseline, flagging an exact tie.

    A tie returns the alphabetically first tied label for convenience but sets
    ``tie`` true so a report can state the tie instead of an arbitrary pick.
    """

    counts = label_distribution(labels)
    total = sum(counts.values())
    if total == 0:
        return {"label": None, "accuracy": 0.0, "tie": False, "counts": counts}
    top = max(counts.values())
    winners = sorted(label for label, count in counts.items() if count == top)
    return {
        "label": winners[0],
        "accuracy": top / total,
        "tie": len(winners) > 1,
        "counts": counts,
    }


__all__ = [
    "HEARSAY_PROMPT_VERSION",
    "SUBTASK_NAMES",
    "SUBTASK_SPECS",
    "assign_case_splits",
    "canonicalize_hearsay_rows",
    "canonicalize_subtask_rows",
    "case_split",
    "label_distribution",
    "majority_baseline",
]
