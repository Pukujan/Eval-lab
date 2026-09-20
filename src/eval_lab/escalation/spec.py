"""Repository-owned typed System-One semantics."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from eval_lab.jev import build_direct_request
from eval_lab.schema import JudgeRecord, JudgmentMode, PairwiseLabel


class TypedQuestion(BaseModel):
    """A backend-neutral typed question with an explicit legal label space."""

    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1)
    question_type: Literal["choice", "boolean"]
    instructions: str = Field(min_length=1)
    legal_labels: list[str] = Field(min_length=2)
    score_order: list[str] = Field(min_length=2)
    boolean_semantics: dict[str, str] | None = None

    def __init__(self, **data: object) -> None:
        super().__init__(**data)
        if len(set(self.legal_labels)) != len(self.legal_labels):
            raise ValueError("legal_labels must be unique")
        if self.score_order != self.legal_labels:
            raise ValueError("score_order must exactly match legal_labels")


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
                        label: label for label in question.legal_labels
                    },
                }
                for key, question in self.questions.items()
            },
        }


def build_decision_spec(record: JudgeRecord, *, context_limit: int = 4096) -> DecisionSpec:
    """Compile a canonical record into the single typed semantic contract."""

    request = build_direct_request(record)
    question_id = next(iter(request["questions"]))
    question_payload = request["questions"][question_id]
    if record.mode is JudgmentMode.SINGLE:
        labels = ["pass", "fail"]
    else:
        labels = [item.value for item in PairwiseLabel]
    question = TypedQuestion(
        question_id=question_id,
        question_type="choice",
        instructions=str(question_payload["instructions"]),
        legal_labels=labels,
        score_order=labels,
    )
    return DecisionSpec(
        spec_id="eval-lab-system-one",
        spec_version="0.1.0",
        record_id=record.record_id,
        state=str(request["state"]),
        questions={question_id: question},
        context_limit=context_limit,
    )


__all__ = ["DecisionSpec", "TypedQuestion", "build_decision_spec"]
