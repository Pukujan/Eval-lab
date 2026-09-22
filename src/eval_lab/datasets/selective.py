"""Deterministic source-family records for EvalLab-Select."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from eval_lab.datasets.arc import ArcSourceMetadata, canonicalize_arc_row
from eval_lab.datasets.synthetic import SyntheticFixture
from eval_lab.schema import (
    GoldLabel,
    GoldProvenance,
    JudgeRecord,
    JudgmentMode,
    RubricCriterion,
    SourceRecord,
    Split,
)

SELECTIVE_CANONICALIZATION_VERSION = "eval-lab-select-single-v1"
SELECTIVE_DATASET_ID = "EvalLab-Select"
SELECTIVE_RUBRIC_ID = "answer-key-correctness"


def arc_single_records(
    rows: Sequence[Mapping[str, Any]],
    *,
    upstream_split: str,
    metadata: ArcSourceMetadata,
) -> tuple[list[SourceRecord], list[JudgeRecord]]:
    """Convert each ARC source into exactly one correct and one incorrect record."""

    sources: list[SourceRecord] = []
    records: list[JudgeRecord] = []
    for row in rows:
        source, pair = canonicalize_arc_row(row, upstream_split=upstream_split, metadata=metadata)
        answer_key = str(source.reference_answer["answer_key"])
        correct = f"{answer_key}) {source.reference_answer['choices'][answer_key]}"
        choices = source.reference_answer["choices"]
        wrong_candidates = [f"{label}) {text}" for label, text in choices.items() if label != answer_key]
        if len(wrong_candidates) != len(set(wrong_candidates)) or not wrong_candidates:
            raise ValueError(f"ARC source {source.source_problem_id} has no unique wrong candidate")
        wrong = wrong_candidates[0]
        for suffix, candidate, label in (("correct", correct, "pass"), ("wrong", wrong, "fail")):
            records.append(
                JudgeRecord(
                    record_id=f"arc-single:{source.source_problem_id}:{suffix}",
                    source_problem_id=source.source_problem_id,
                    mode=JudgmentMode.SINGLE,
                    prompt=source.prompt,
                    rubric=[
                        RubricCriterion(
                            criterion_id=SELECTIVE_RUBRIC_ID,
                            description="The candidate selects the answer-key choice.",
                            weight=1.0,
                            aggregation_rule="all",
                        )
                    ],
                    candidate_a=candidate,
                    gold=GoldLabel(
                        label=label,
                        provenance=GoldProvenance.ANSWER_KEY,
                        evidence={
                            "source_problem_id": source.source_problem_id,
                            "answer_key": answer_key,
                            "variant": suffix,
                            "pair_record_id": pair.record_id,
                        },
                        verifier_id="arc-answer-key-v1",
                    ),
                    split=source.split,
                    perturbation={
                        "kind": "correct_or_deterministic_wrong_choice",
                        "source_record_id": pair.record_id,
                        "source_dataset": source.source_dataset,
                        "resolved_revision": metadata.resolved_revision,
                        "canonicalization_version": SELECTIVE_CANONICALIZATION_VERSION,
                    },
                )
            )
        sources.append(source)
    return sources, records


def combine_selective_records(
    *,
    arc_sources: Sequence[SourceRecord],
    arc_records: Sequence[JudgeRecord],
    synthetic: SyntheticFixture,
) -> tuple[list[SourceRecord], list[JudgeRecord]]:
    """Combine disjoint ARC and synthetic source families with strict identity checks."""

    sources = list(arc_sources) + list(synthetic.sources)
    records = list(arc_records) + [record for record in synthetic.records if record.mode is JudgmentMode.SINGLE]
    source_ids = [source.source_problem_id for source in sources]
    record_ids = [record.record_id for record in records]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("selective benchmark source families must be unique")
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("selective benchmark record IDs must be unique")
    return sources, records


def partition_records(records: Sequence[JudgeRecord]) -> dict[str, list[JudgeRecord]]:
    """Return frozen threshold and final partitions without resampling records."""

    threshold = [record for record in records if record.split is not Split.TEST]
    final = [record for record in records if record.split is Split.TEST]
    if not threshold or not final:
        raise ValueError("selective benchmark requires both threshold and final partitions")
    threshold_ids = {record.record_id for record in threshold}
    final_ids = {record.record_id for record in final}
    if threshold_ids & final_ids:
        raise ValueError("threshold and final record IDs overlap")
    threshold_sources = {record.source_problem_id for record in threshold}
    final_sources = {record.source_problem_id for record in final}
    if threshold_sources & final_sources:
        raise ValueError("threshold and final source families overlap")
    return {"threshold_selection": threshold, "final_evaluation": final}


__all__ = [
    "SELECTIVE_CANONICALIZATION_VERSION",
    "SELECTIVE_DATASET_ID",
    "arc_single_records",
    "combine_selective_records",
    "partition_records",
]
