"""Repository-owned typed System-One semantics."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from eval_lab.schema import JudgeRecord, JudgmentMode, PairwiseLabel


class TypedQuestion(BaseModel):
    """A backend-neutral typed question with an explicit legal label space."""

    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1)
    question_type: Literal["choice", "boolean"]
    instructions: str = Field(min_length=1)
    legal_labels: list[str] = Field(min_length=2)
    score_order: list[str] = Field(min_length=2)
    criteria: dict[str, str] = Field(default_factory=dict)
    boolean_semantics: dict[str, str] | None = None

    def __init__(self, **data: object) -> None:
        super().__init__(**data)
        if len(set(self.legal_labels)) != len(self.legal_labels):
            raise ValueError("legal_labels must be unique")
        if self.score_order != self.legal_labels:
            raise ValueError("score_order must exactly match legal_labels")
        if self.criteria and set(self.criteria) != set(self.legal_labels):
            raise ValueError("criteria keys must exactly match legal_labels")


class DecisionSpec(BaseModel):
    """Typed decision request shared by Jev and System-One adapters."""

    model_config = ConfigDict(extra="forbid")

    spec_id: str = Field(min_length=1)
    spec_version: str = Field(min_length=1)
    record_id: str = Field(min_length=1)
    state: str = Field(min_length=1)
    questions: dict[str, TypedQuestion] = Field(min_length=1)
    context_limit: int = Field(gt=0)

    @property
    def primary_question(self) -> TypedQuestion:
        return next(iter(self.questions.values()))

    @property
    def legal_labels(self) -> list[str]:
        return list(self.primary_question.legal_labels)

    def provider_payload(self) -> dict[str, object]:
        """Return the stable state/questions shape used by typed providers."""

        return {
            "state": self.state,
            "questions": {
                key: {
                    "type": question.question_type,
                    "instructions": question.instructions,
                    "criteria": {
                        label: question.criteria.get(label, label)
                        for label in question.legal_labels
                    },
                }
                for key, question in self.questions.items()
            },
        }


def _state_for_record(record: JudgeRecord) -> str:
    """Build the benchmark state without importing the historical Jev adapter."""

    state = f"User prompt: {record.prompt}\nCandidate A: {record.candidate_a}"
    if record.mode is JudgmentMode.PAIRWISE:
        state += f"\nCandidate B: {record.candidate_b}"
    return state


def _choice_criteria(record: JudgeRecord) -> dict[str, str]:
    """Describe the closed label space in provider-neutral terms."""

    if record.mode is JudgmentMode.SINGLE:
        return {
            "pass": "The candidate is objectively correct.",
            "fail": "The candidate is objectively incorrect.",
        }
    return {
        PairwiseLabel.A.value: "Candidate A is better or more correct.",
        PairwiseLabel.B.value: "Candidate B is better or more correct.",
        PairwiseLabel.TIE.value: "The candidates are objectively equivalent.",
    }


def build_decision_spec(
    record: JudgeRecord,
    *,
    context_limit: int = 4096,
    label_order: Sequence[str] | None = None,
    instruction_override: str | None = None,
) -> DecisionSpec:
    """Compile a canonical record into the single typed semantic contract."""

    question_id = "verdict"
    if record.mode is JudgmentMode.SINGLE:
        labels = ["pass", "fail"]
    else:
        labels = [item.value for item in PairwiseLabel]
    if label_order is not None:
        ordered = list(label_order)
        if set(ordered) != set(labels) or len(ordered) != len(labels):
            raise ValueError("label_order must be a permutation of the legal labels")
        labels = ordered
    question = TypedQuestion(
        question_id=question_id,
        question_type="choice",
        instructions=instruction_override
        or "Return the single objective verdict for the candidate record.",
        legal_labels=labels,
        score_order=labels,
        criteria={label: _choice_criteria(record)[label] for label in labels},
    )
    return DecisionSpec(
        spec_id="eval-lab-system-one",
        spec_version="0.1.0",
        record_id=record.record_id,
        state=_state_for_record(record),
        questions={question_id: question},
        context_limit=context_limit,
    )


__all__ = ["DecisionSpec", "TypedQuestion", "build_decision_spec"]
