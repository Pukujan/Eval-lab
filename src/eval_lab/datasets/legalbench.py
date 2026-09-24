"""Canonicalize the fixed-label LegalBench Hearsay task."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
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


__all__ = ["HEARSAY_PROMPT_VERSION", "canonicalize_hearsay_rows"]
