"""Canonicalize frozen GLEIF registry facts into objective claim pairs.

GLEIF Level 1 (LEI) and Level 2 (Relationship Record) facts are frozen source
records, so the gold label is a deterministic transform of the source, not a
model judgment. Single-mode judges here answer a closed ``pass``/``fail``
verdict on one candidate claim, so every task family is expressed as a
claim-verification pair: the source record is shown as evidence and one record
asserts the true fact (gold ``pass``) while one asserts a deterministic
perturbation of it (gold ``fail``).

The split unit is the entity: a claim's split depends only on its normalized
LEI, so no entity crosses the calibration/test boundary and generated aliases
inherit their source entity's split.
"""

from __future__ import annotations

import csv
import hashlib
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from eval_lab.schema import (
    GoldLabel,
    GoldProvenance,
    JudgeRecord,
    JudgmentMode,
    RubricCriterion,
    Split,
)

DATASET = "gleif"
SPLIT_FAMILY = "gleif"
VERIFIER_ID = "gleif-registry-facts-v1"
PROMPT_VERSION = "gleif-registry-facts-v1"
_LEI_RE = re.compile(r"^[0-9A-Z]{20}$")


@dataclass(frozen=True)
class GleifEntity:
    """The Level 1 fields the objective task families consume."""

    lei: str
    legal_name: str
    entity_category: str
    legal_jurisdiction: str
    registration_status: str
    initial_registration_date: str


def normalize_lei(value: str) -> str:
    """Return the canonical LEI form used for identity and split hashing."""

    return value.strip().upper()


def entity_split(lei: str, *, seed: int) -> Split:
    """Assign an entity to calibration or test using only its normalized LEI."""

    normalized = normalize_lei(lei)
    if not _LEI_RE.match(normalized):
        raise ValueError(f"not a well-formed LEI: {lei!r}")
    digest = hashlib.sha256(f"{seed}:{SPLIT_FAMILY}:{normalized}".encode()).digest()
    sample = int.from_bytes(digest[:8], byteorder="big") / float(2**64)
    return Split.CALIBRATION if sample < 0.5 else Split.TEST


def _rubric() -> list[RubricCriterion]:
    return [
        RubricCriterion(
            criterion_id="gleif-registry-fact",
            description="The candidate claim matches the frozen GLEIF source record.",
            weight=1.0,
            aggregation_rule="single_label",
        )
    ]


def _context(entity: GleifEntity) -> str:
    return (
        "GLEIF Level 1 record\n"
        f"LEI: {normalize_lei(entity.lei)}\n"
        f"Legal name: {entity.legal_name}\n"
        f"Entity category: {entity.entity_category}\n"
        f"Legal jurisdiction: {entity.legal_jurisdiction}\n"
        f"Registration status: {entity.registration_status}\n"
        f"Initial registration date: {entity.initial_registration_date}"
    )


def _claim(
    *,
    family: str,
    lei: str,
    context: str,
    question: str,
    true_value: str,
    wrong_value: str,
    seed: int,
    evidence: Mapping[str, Any],
    problem_key: str | None = None,
) -> list[JudgeRecord]:
    normalized = normalize_lei(lei)
    if true_value == wrong_value:
        raise ValueError(f"{family}: wrong variant must differ from the true value")
    source_problem_id = problem_key if problem_key is not None else f"{family}:{normalized}"
    split = entity_split(normalized, seed=seed)
    prompt = f"{context}\n\nQuestion: {question}"
    shared = {
        "source_problem_id": source_problem_id,
        "prompt": prompt,
        "rubric": _rubric(),
        "split": split,
    }
    records = []
    for variant, candidate, correct in (
        ("correct", true_value, True),
        ("wrong", wrong_value, False),
    ):
        records.append(
            JudgeRecord(
                record_id=f"{DATASET}:{source_problem_id}:{variant}",
                mode=JudgmentMode.SINGLE,
                candidate_a=f"Answer: {candidate}",
                gold=GoldLabel(
                    label="pass" if correct else "fail",
                    provenance=GoldProvenance.DETERMINISTIC_VERIFIER,
                    evidence={
                        "family": family,
                        "entity_lei": normalized,
                        "source_field_value": true_value,
                        "candidate_value": candidate,
                        **evidence,
                    },
                    verifier_id=VERIFIER_ID,
                ),
                perturbation={
                    "kind": "correct_or_deterministic_wrong_registry_fact",
                    "variant": variant,
                    "family": family,
                },
                **shared,
            )
        )
    return records


def _alternative(value: str, alternatives: Sequence[str]) -> str | None:
    for candidate in sorted({item for item in alternatives if item}):
        if candidate != value:
            return candidate
    return None


def status_claims(
    entity: GleifEntity, *, status_vocabulary: Sequence[str], seed: int
) -> list[JudgeRecord]:
    wrong = _alternative(entity.registration_status, status_vocabulary)
    if wrong is None:
        return []
    return _claim(
        family="status",
        lei=entity.lei,
        context=_context(entity),
        question="Is the recorded registration status correct?",
        true_value=entity.registration_status,
        wrong_value=wrong,
        seed=seed,
        evidence={"field": "RegistrationStatus"},
    )


def jurisdiction_claims(
    entity: GleifEntity, *, jurisdiction_vocabulary: Sequence[str], seed: int
) -> list[JudgeRecord]:
    wrong = _alternative(entity.legal_jurisdiction, jurisdiction_vocabulary)
    if wrong is None:
        return []
    return _claim(
        family="jurisdiction",
        lei=entity.lei,
        context=_context(entity),
        question="Is the recorded legal jurisdiction correct?",
        true_value=entity.legal_jurisdiction,
        wrong_value=wrong,
        seed=seed,
        evidence={"field": "LegalJurisdiction"},
    )


def category_claims(
    entity: GleifEntity, *, category_vocabulary: Sequence[str], seed: int
) -> list[JudgeRecord]:
    wrong = _alternative(entity.entity_category, category_vocabulary)
    if wrong is None:
        return []
    return _claim(
        family="entity-category",
        lei=entity.lei,
        context=_context(entity),
        question="Is the recorded entity category correct?",
        true_value=entity.entity_category,
        wrong_value=wrong,
        seed=seed,
        evidence={"field": "EntityCategory"},
    )


def registration_date_claims(entity: GleifEntity, *, seed: int) -> list[JudgeRecord]:
    try:
        parsed = date.fromisoformat(entity.initial_registration_date)
    except ValueError:
        return []
    return _claim(
        family="initial-registration-date",
        lei=entity.lei,
        context=_context(entity),
        question="Is the recorded initial registration date correct?",
        true_value=entity.initial_registration_date,
        wrong_value=(parsed + timedelta(days=1)).isoformat(),
        seed=seed,
        evidence={"field": "InitialRegistrationDate"},
    )


def alias_claims(
    entity: GleifEntity, *, alias: str, wrong_lei: str, seed: int
) -> list[JudgeRecord]:
    normalized = normalize_lei(entity.lei)
    other = normalize_lei(wrong_lei)
    if other == normalized:
        raise ValueError("alias distractor LEI must differ from the entity LEI")
    return _claim(
        family="alias",
        lei=normalized,
        context=_context(entity),
        question=f"Does the name variant {alias!r} resolve to this record's LEI?",
        true_value=normalized,
        wrong_value=other,
        seed=seed,
        evidence={"field": "LegalName", "alias": alias},
    )


def parent_claims(
    *,
    start_lei: str,
    start_name: str,
    parent_lei: str,
    wrong_lei: str,
    relationship_type: str,
    seed: int,
) -> list[JudgeRecord]:
    normalized = normalize_lei(start_lei)
    parent = normalize_lei(parent_lei)
    other = normalize_lei(wrong_lei)
    if other in {normalized, parent}:
        raise ValueError("parent distractor LEI must differ from both nodes")
    context = (
        "GLEIF Level 2 relationship record\n"
        f"Start node (child): {normalized} ({start_name})\n"
        f"Relationship type: {relationship_type}"
    )
    return _claim(
        family="parent",
        lei=normalized,
        context=context,
        question="Is the recorded parent (end node) LEI correct?",
        true_value=parent,
        wrong_value=other,
        seed=seed,
        problem_key=f"parent:{normalized}:{parent}:{relationship_type}",
        evidence={
            "field": "Relationship.EndNode.NodeID",
            "relationship_type": relationship_type,
            "parent_lei": parent,
        },
    )


def missing_columns(header: Sequence[str], required: Mapping[str, str]) -> list[str]:
    """Return the logical column names whose actual header names are absent."""

    present = set(header)
    return sorted(logical for logical, actual in required.items() if actual not in present)


def iter_entities(
    csv_path: Path, *, columns: Mapping[str, str], limit: int | None = None
) -> Iterator[GleifEntity]:
    """Stream Level 1 entities from a frozen GLEIF CSV using an explicit column map."""

    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError(f"empty CSV: {csv_path.name}") from exc
        absent = missing_columns(header, columns)
        if absent:
            raise ValueError(f"{csv_path.name} is missing required columns: {absent}")
        index = {logical: header.index(actual) for logical, actual in columns.items()}
        emitted = 0
        for row in reader:
            if len(row) != len(header):
                raise ValueError(f"{csv_path.name}: ragged row with {len(row)} fields")
            entity = GleifEntity(
                lei=row[index["lei"]],
                legal_name=row[index["legal_name"]],
                entity_category=row[index["entity_category"]],
                legal_jurisdiction=row[index["legal_jurisdiction"]],
                registration_status=row[index["registration_status"]],
                initial_registration_date=row[index["initial_registration_date"]],
            )
            if not _LEI_RE.match(normalize_lei(entity.lei)):
                continue
            yield entity
            emitted += 1
            if limit is not None and emitted >= limit:
                return


__all__ = [
    "DATASET",
    "PROMPT_VERSION",
    "SPLIT_FAMILY",
    "VERIFIER_ID",
    "GleifEntity",
    "alias_claims",
    "category_claims",
    "entity_split",
    "iter_entities",
    "jurisdiction_claims",
    "missing_columns",
    "normalize_lei",
    "parent_claims",
    "registration_date_claims",
    "status_claims",
]
