"""Small, reproducible text-judge training primitives for TASK-0009."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from eval_lab.schema import JudgePrediction, JudgeRecord, Split

CLASS_ORDER = ("pass", "fail")
STUDENT_ID = "tfidf-logistic-v1"
PROTOCOL_VERSION = "task-0009-single-correctness-v1"


@dataclass(frozen=True)
class TrainingRow:
    """One auditable row used to fit a student arm."""

    row_id: str
    record_id: str
    source_problem_id: str
    source_split: str
    domain: str
    prompt: str
    candidate: str
    label: str
    criterion_text: str
    provenance: str
    source_kind: str
    augmentation: str

    def to_text(self) -> str:
        """Render the row into the student's bounded text input."""

        return (
            "Task: decide whether the candidate satisfies the rubric.\n"
            f"Rubric: {self.criterion_text}\n"
            f"Domain: {self.domain}\n"
            f"Prompt: {self.prompt}\n"
            f"Candidate: {self.candidate}"
        )


def record_to_text(record: JudgeRecord, *, criterion_text: str | None = None) -> str:
    """Render one canonical single-answer record for inference."""

    if record.mode.value != "single":
        raise ValueError("TASK-0009 student scope is single-answer records")
    criterion = criterion_text or record.rubric[0].description
    return (
        "Task: decide whether the candidate satisfies the rubric.\n"
        f"Rubric: {criterion}\n"
        f"Prompt: {record.prompt}\n"
        f"Candidate: {record.candidate_a}"
    )


def _row_from_record(
    record: JudgeRecord,
    *,
    criterion_text: str,
    augmentation: str,
) -> TrainingRow:
    source = record.source_problem_id
    return TrainingRow(
        row_id=f"{record.record_id}:{augmentation}",
        record_id=record.record_id,
        source_problem_id=source,
        source_split=record.split.value,
        domain=_domain_for_record(record),
        prompt=record.prompt,
        candidate=record.candidate_a,
        label=record.gold.label,
        criterion_text=criterion_text,
        provenance=record.gold.provenance.value,
        source_kind="objective",
        augmentation=augmentation,
    )


def _hard_negative_row(
    item: Mapping[str, Any],
    *,
    criterion_text: str,
    augmentation: str,
) -> TrainingRow:
    gold = item.get("gold")
    if not isinstance(gold, Mapping) or gold.get("label") != "fail":
        raise ValueError("hard negatives must carry deterministic fail labels")
    if gold.get("provenance") != "deterministic_verifier":
        raise ValueError("hard negatives must retain deterministic verifier provenance")
    source_split = str(item.get("split", ""))
    if source_split == Split.TEST.value:
        raise ValueError("test hard negatives cannot enter training")
    return TrainingRow(
        row_id=f"{item['record_id']}:{augmentation}",
        record_id=str(item["record_id"]),
        source_problem_id=str(item["source_problem_id"]),
        source_split=source_split,
        domain=str(item["domain"]),
        prompt=str(item["prompt"]),
        candidate=str(item["candidate"]),
        label="fail",
        criterion_text=criterion_text,
        provenance="deterministic_verifier",
        source_kind="verified_hard_negative",
        augmentation=augmentation,
    )


def build_training_rows(
    records: Sequence[JudgeRecord],
    *,
    arm: str,
    hard_negatives: Sequence[Mapping[str, Any]] = (),
    rubric_paraphrases: Mapping[str, str] | None = None,
) -> list[TrainingRow]:
    """Build one leakage-safe training arm from train-split single records."""

    if arm not in {"A", "B", "C", "D"}:
        raise ValueError("training arm must be A, B, C, or D")
    include_criteria = arm in {"B", "D"}
    include_hard = arm in {"C", "D"}
    paraphrases = dict(rubric_paraphrases or {})
    rows: list[TrainingRow] = []

    for record in records:
        if record.mode.value != "single" or record.split is not Split.TRAIN:
            continue
        canonical = record.rubric[0].description
        rows.append(_row_from_record(record, criterion_text=canonical, augmentation="canonical"))
        if include_criteria:
            domain = _domain_for_record(record)
            paraphrase = paraphrases.get(domain)
            if paraphrase:
                rows.append(
                    _row_from_record(
                        record,
                        criterion_text=paraphrase,
                        augmentation=f"criterion-paraphrase:{domain}",
                    )
                )

    if include_hard:
        for item in hard_negatives:
            if str(item.get("split")) != Split.TRAIN.value:
                continue
            canonical = "The candidate matches the deterministic answer key."
            rows.append(
                _hard_negative_row(
                    item,
                    criterion_text=canonical,
                    augmentation="verified-hard-negative",
                )
            )
            if include_criteria:
                domain = str(item["domain"])
                paraphrase = paraphrases.get(domain)
                if paraphrase:
                    rows.append(
                        _hard_negative_row(
                            item,
                            criterion_text=paraphrase,
                            augmentation=f"criterion-paraphrase:{domain}",
                        )
                    )

    if not rows:
        raise ValueError(f"arm {arm} has no training rows")
    if any(row.source_split == Split.TEST.value for row in rows):
        raise ValueError("test source entered training rows")
    if len({row.row_id for row in rows}) != len(rows):
        raise ValueError("training row IDs must be unique")
    return rows


def _domain_for_record(record: JudgeRecord) -> str:
    """Recover the synthetic domain from stable verifier metadata when present."""

    verifier = record.gold.verifier_id or ""
    return {
        "arithmetic-v1": "arithmetic",
        "multiple-choice-v1": "multiple_choice",
        "structured-output-v1": "structured",
        "code-output-v1": "code_output",
    }.get(verifier, "unknown")


def training_row_fingerprint(rows: Sequence[TrainingRow]) -> str:
    """Hash the complete, ordered training manifest."""

    payload = json.dumps([asdict(row) for row in rows], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TextLogisticStudent:
    """A compact serialized TF-IDF/logistic student with normalized probabilities."""

    def __init__(self, *, seed: int = 20260920) -> None:
        self.seed = seed
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            sublinear_tf=True,
            token_pattern=r"(?u)\b\w[\w'-]*\b",
        )
        self.classifier = LogisticRegression(
            max_iter=1000,
            random_state=seed,
            solver="liblinear",
            class_weight="balanced",
        )
        self.training_row_count = 0
        self.training_row_fingerprint = ""

    def fit(self, rows: Sequence[TrainingRow]) -> TextLogisticStudent:
        if not rows:
            raise ValueError("student training rows must not be empty")
        if any(row.label not in CLASS_ORDER for row in rows):
            raise ValueError("student labels must be pass or fail")
        texts = [row.to_text() for row in rows]
        self.vectorizer.fit(texts)
        matrix = self.vectorizer.transform(texts)
        self.classifier.fit(matrix, [row.label for row in rows])
        self.training_row_count = len(rows)
        self.training_row_fingerprint = training_row_fingerprint(rows)
        return self

    def predict(self, records: Sequence[JudgeRecord]) -> list[JudgePrediction]:
        if not self.training_row_count:
            raise RuntimeError("student must be fit before prediction")
        if not records:
            return []
        start = perf_counter()
        matrix = self.vectorizer.transform([record_to_text(record) for record in records])
        probabilities = self.classifier.predict_proba(matrix)
        elapsed_ms = (perf_counter() - start) * 1000
        class_indices = {str(label): index for index, label in enumerate(self.classifier.classes_)}
        feature_count = len(self.vectorizer.vocabulary_)
        per_record_ms = elapsed_ms / len(records)
        output: list[JudgePrediction] = []
        for record, row in zip(records, probabilities, strict=True):
            mapped = {label: float(row[class_indices[label]]) for label in CLASS_ORDER}
            label = max(CLASS_ORDER, key=lambda item: mapped[item])
            raw_scores = {key: math.log(max(value, 1e-15)) for key, value in mapped.items()}
            output.append(
                JudgePrediction(
                    record_id=record.record_id,
                    judge_id=STUDENT_ID,
                    protocol_version=PROTOCOL_VERSION,
                    label=label,
                    probabilities=mapped,
                    raw_scores=raw_scores,
                    latency_ms=per_record_ms,
                    provider_metadata={
                        "student_id": STUDENT_ID,
                        "feature_count": feature_count,
                        "training_row_count": self.training_row_count,
                        "training_row_fingerprint": self.training_row_fingerprint,
                        "scope": "single-answer correctness",
                    },
                )
            )
        return output

    def artifact(self) -> dict[str, Any]:
        """Return a JSON-safe model artifact without pickle or external weights."""

        vocabulary = {str(key): int(value) for key, value in self.vectorizer.vocabulary_.items()}
        return {
            "student_id": STUDENT_ID,
            "protocol_version": PROTOCOL_VERSION,
            "seed": self.seed,
            "training_row_count": self.training_row_count,
            "training_row_fingerprint": self.training_row_fingerprint,
            "vectorizer": {
                "lowercase": True,
                "ngram_range": [1, 2],
                "sublinear_tf": True,
                "vocabulary": vocabulary,
                "idf": [float(value) for value in self.vectorizer.idf_],
            },
            "classifier": {
                "classes": [str(value) for value in self.classifier.classes_],
                "coef": [[float(value) for value in row] for row in self.classifier.coef_],
                "intercept": [float(value) for value in self.classifier.intercept_],
                "solver": "liblinear",
                "class_weight": "balanced",
            },
        }


__all__ = [
    "CLASS_ORDER",
    "PROTOCOL_VERSION",
    "STUDENT_ID",
    "TextLogisticStudent",
    "TrainingRow",
    "build_training_rows",
    "record_to_text",
    "training_row_fingerprint",
]
