"""Reproducible ARC-Challenge retrieval and canonicalization."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from eval_lab.schema import (
    GoldLabel,
    GoldProvenance,
    JudgeRecord,
    JudgmentMode,
    PairwiseLabel,
    RubricCriterion,
    SourceRecord,
    Split,
)

ARC_DATASET_ID = "allenai/ai2_arc"
ARC_CONFIG = "ARC-Challenge"
ARC_LICENSE = "CC BY-SA 4.0"
ARC_CANONICALIZATION_VERSION = "arc-challenge-canonical-v1"
ARC_SPLIT_POLICY = {
    "train": "train",
    "validation": "dev_or_calibration_by_source_id",
    "test": "test",
}


@dataclass(frozen=True)
class ArcAdapterConfig:
    """Inputs that affect source resolution and canonical record identity."""

    dataset_id: str = ARC_DATASET_ID
    config: str = ARC_CONFIG
    expected_license: str = ARC_LICENSE
    requested_revision: str = "main"
    canonicalization_version: str = ARC_CANONICALIZATION_VERSION
    split_seed: int = 20260920
    validation_dev_fraction: float = 0.5


_DEFAULT_CONFIG = ArcAdapterConfig()


class ArcSourceMetadata(BaseModel):
    """Pinned source facts required to reproduce an ARC conversion."""

    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(min_length=1)
    config: str = Field(min_length=1)
    license: str = Field(min_length=1)
    requested_revision: str = Field(min_length=1)
    resolved_revision: str = Field(min_length=1)
    canonicalization_version: str = Field(min_length=1)
    split_policy: dict[str, str]
    split_seed: int
    validation_dev_fraction: float = Field(gt=0, lt=1)
    fingerprint: str | None = None

    @model_validator(mode="after")
    def validate_license(self) -> ArcSourceMetadata:
        if normalize_license(self.license) != ARC_LICENSE:
            raise ValueError("ARC source license must be CC BY-SA 4.0")
        return self


class ArcAdapterResult(BaseModel):
    """Canonical ARC output plus the small manifest used to select it."""

    model_config = ConfigDict(extra="forbid")

    metadata: ArcSourceMetadata
    sources: list[SourceRecord]
    records: list[JudgeRecord]
    slice_manifest: dict[str, Any]

    @property
    def fingerprint(self) -> str:
        if self.metadata.fingerprint is None:
            raise ValueError("adapter result metadata has no fingerprint")
        return self.metadata.fingerprint


def normalize_license(value: str | Sequence[str]) -> str:
    """Normalize common Hugging Face license spellings."""

    if isinstance(value, Sequence) and not isinstance(value, str):
        value = value[0] if value else ""
    normalized = str(value).strip().lower().replace("_", "-")
    if normalized in {"cc-by-sa-4.0", "cc by-sa 4.0", "cc-by-sa-4"}:
        return ARC_LICENSE
    return str(value).strip()


def _metadata_license(payload: Mapping[str, Any]) -> str:
    card_data = payload.get("cardData") or payload.get("card_data") or {}
    raw = card_data.get("license") or payload.get("license") or ""
    if isinstance(raw, Mapping):
        raw = raw.get("id") or raw.get("name") or ""
    license_name = normalize_license(raw)
    if license_name != ARC_LICENSE:
        raise ValueError(f"expected ARC license {ARC_LICENSE!r}, got {license_name!r}")
    return license_name


def resolve_arc_source_metadata(
    config: ArcAdapterConfig = _DEFAULT_CONFIG,
    *,
    payload: Mapping[str, Any] | None = None,
    get: Callable[..., Any] = httpx.get,
) -> ArcSourceMetadata:
    """Resolve `main` or another requested revision to an immutable commit SHA."""

    if payload is None:
        url = f"https://huggingface.co/api/datasets/{config.dataset_id}"
        response = get(url, params={"revision": config.requested_revision}, timeout=30.0)
        response.raise_for_status()
        payload = response.json()
    resolved_revision = str(payload.get("sha") or payload.get("oid") or payload.get("commit", ""))
    if not resolved_revision:
        raise ValueError("Hugging Face metadata did not contain a resolved revision SHA")
    return ArcSourceMetadata(
        dataset_id=config.dataset_id,
        config=config.config,
        license=_metadata_license(payload),
        requested_revision=config.requested_revision,
        resolved_revision=resolved_revision,
        canonicalization_version=config.canonicalization_version,
        split_policy=dict(ARC_SPLIT_POLICY),
        split_seed=config.split_seed,
        validation_dev_fraction=config.validation_dev_fraction,
    )


def load_arc_rows(
    upstream_split: str,
    *,
    metadata: ArcSourceMetadata,
    cache_dir: str | Path | None = None,
) -> Any:
    """Load one exact source split lazily through `datasets` when requested."""

    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("install the optional `datasets` package to retrieve ARC rows") from exc
    kwargs: dict[str, Any] = {
        "path": metadata.dataset_id,
        "name": metadata.config,
        "split": upstream_split,
        "revision": metadata.resolved_revision,
    }
    if cache_dir is not None:
        kwargs["cache_dir"] = str(cache_dir)
    return load_dataset(**kwargs)


def map_arc_split(
    upstream_split: str,
    source_problem_id: str,
    *,
    seed: int = 20260920,
    validation_dev_fraction: float = 0.5,
) -> Split:
    """Map an upstream split without allowing one source ID to cross splits."""

    if not 0 < validation_dev_fraction < 1:
        raise ValueError("validation_dev_fraction must be between 0 and 1")
    normalized = upstream_split.lower()
    if normalized == "train":
        return Split.TRAIN
    if normalized in {"test", "testing"}:
        return Split.TEST
    if normalized in {"validation", "valid", "dev"}:
        digest = hashlib.sha256(f"{seed}:{source_problem_id}:validation".encode()).digest()
        sample = int.from_bytes(digest[:8], "big") / float(2**64)
        return Split.DEV if sample < validation_dev_fraction else Split.CALIBRATION
    raise ValueError(f"unsupported ARC upstream split: {upstream_split}")


def _choice_data(row: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    choices = row.get("choices")
    if isinstance(choices, Mapping):
        labels = [str(label) for label in choices.get("label", [])]
        texts = [str(text) for text in choices.get("text", [])]
    elif isinstance(choices, Sequence) and not isinstance(choices, str):
        labels = [chr(ord("A") + index) for index, _ in enumerate(choices)]
        texts = [str(choice) for choice in choices]
    else:
        raise TypeError("ARC row choices must contain parallel label/text arrays")
    if not labels or len(labels) != len(texts) or len(set(labels)) != len(labels):
        raise ValueError("ARC row choices must have unique parallel labels and texts")
    return labels, texts


def _answer_label(row: Mapping[str, Any], labels: Sequence[str]) -> str:
    answer = str(row.get("answerKey", row.get("answer_key", "")))
    if answer in labels:
        return answer
    if answer.isdigit() and int(answer) < len(labels):
        return labels[int(answer)]
    raise ValueError("ARC answerKey does not match the row choice labels")


def _candidate(label: str, text: str) -> str:
    return f"{label}) {text}"


def canonicalize_arc_row(
    row: Mapping[str, Any],
    *,
    upstream_split: str,
    metadata: ArcSourceMetadata,
) -> tuple[SourceRecord, JudgeRecord]:
    """Convert one ARC-shaped row into one objective pairwise judge record."""

    source_problem_id = str(row.get("id", "")).strip()
    question = str(row.get("question", "")).strip()
    if not source_problem_id or not question:
        raise ValueError("ARC rows require non-empty id and question")
    labels, texts = _choice_data(row)
    answer_label = _answer_label(row, labels)
    answer_index = labels.index(answer_label)
    wrong_labels = [label for label in labels if label != answer_label]
    if not wrong_labels:
        raise ValueError("ARC row requires at least one incorrect choice")
    wrong_digest = hashlib.sha256(f"{metadata.split_seed}:{source_problem_id}:wrong".encode()).digest()
    wrong_label = wrong_labels[int.from_bytes(wrong_digest[:8], "big") % len(wrong_labels)]
    text_by_label = dict(zip(labels, texts, strict=True))
    prompt = "Question: " + question + "\nChoices:\n" + "\n".join(
        _candidate(label, text_by_label[label]) for label in labels
    )
    mapped_split = map_arc_split(
        upstream_split,
        source_problem_id,
        seed=metadata.split_seed,
        validation_dev_fraction=metadata.validation_dev_fraction,
    )
    correct_candidate = _candidate(answer_label, text_by_label[answer_label])
    wrong_candidate = _candidate(wrong_label, text_by_label[wrong_label])
    order_digest = hashlib.sha256(f"{metadata.split_seed}:{source_problem_id}:order".encode()).digest()
    correct_first = order_digest[0] % 2 == 0
    candidate_a, candidate_b = (
        (correct_candidate, wrong_candidate) if correct_first else (wrong_candidate, correct_candidate)
    )
    pair_label = PairwiseLabel.A.value if correct_first else PairwiseLabel.B.value
    source = SourceRecord(
        source_id=f"arc:{source_problem_id}",
        domain="arc_challenge",
        source_dataset=metadata.dataset_id,
        source_problem_id=source_problem_id,
        split=mapped_split,
        prompt=prompt,
        reference_answer={
            "answer_key": answer_label,
            "answer_text": text_by_label[answer_label],
            "choices": dict(zip(labels, texts, strict=True)),
        },
        source_metadata={
            "config": metadata.config,
            "license": metadata.license,
            "requested_revision": metadata.requested_revision,
            "resolved_revision": metadata.resolved_revision,
            "upstream_split": upstream_split,
            "canonicalization_version": metadata.canonicalization_version,
        },
    )
    record = JudgeRecord(
        record_id=f"arc-pair:{source_problem_id}",
        source_problem_id=source_problem_id,
        mode=JudgmentMode.PAIRWISE,
        prompt=prompt,
        rubric=[
            RubricCriterion(
                criterion_id="answer-key-correctness",
                description="Prefer the candidate that selects the answer-key choice.",
                weight=1.0,
                aggregation_rule="all",
            )
        ],
        candidate_a=candidate_a,
        candidate_b=candidate_b,
        gold=GoldLabel(
            label=pair_label,
            provenance=GoldProvenance.ANSWER_KEY,
            evidence={
                "source_problem_id": source_problem_id,
                "answer_key": answer_label,
                "correct_choice_index": answer_index,
                "wrong_choice": wrong_label,
            },
            verifier_id="arc-answer-key-v1",
        ),
        split=mapped_split,
        perturbation={
            "kind": "deterministic_wrong_choice",
            "upstream_split": upstream_split,
            "wrong_choice": wrong_label,
            "split_seed": metadata.split_seed,
        },
    )
    return source, record


def fingerprint_arc_output(
    metadata: ArcSourceMetadata,
    sources: Sequence[SourceRecord],
    records: Sequence[JudgeRecord],
) -> str:
    """Fingerprint source pinning plus canonical output, excluding the fingerprint itself."""

    payload = {
        "metadata": metadata.model_dump(mode="json", exclude={"fingerprint"}),
        "sources": [source.model_dump(mode="json") for source in sources],
        "records": [record.model_dump(mode="json") for record in records],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_arc_dataset(
    rows_by_split: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    metadata: ArcSourceMetadata,
) -> ArcAdapterResult:
    """Canonicalize mocked or retrieved rows and create a small slice manifest."""

    sources: list[SourceRecord] = []
    records: list[JudgeRecord] = []
    seen_ids: set[str] = set()
    for upstream_split, rows in rows_by_split.items():
        for row in rows:
            source, record = canonicalize_arc_row(row, upstream_split=upstream_split, metadata=metadata)
            if source.source_problem_id in seen_ids:
                raise ValueError(f"duplicate ARC source id: {source.source_problem_id}")
            seen_ids.add(source.source_problem_id)
            sources.append(source)
            records.append(record)
    if not records:
        raise ValueError("ARC slice must contain at least one row")
    fingerprint = fingerprint_arc_output(metadata, sources, records)
    pinned_metadata = metadata.model_copy(update={"fingerprint": fingerprint})
    split_counts = Counter(source.split.value for source in sources)
    manifest = {
        "dataset_id": pinned_metadata.dataset_id,
        "config": pinned_metadata.config,
        "license": pinned_metadata.license,
        "requested_revision": pinned_metadata.requested_revision,
        "resolved_revision": pinned_metadata.resolved_revision,
        "canonicalization_version": pinned_metadata.canonicalization_version,
        "split_policy": pinned_metadata.split_policy,
        "split_seed": pinned_metadata.split_seed,
        "validation_dev_fraction": pinned_metadata.validation_dev_fraction,
        "split_counts": dict(sorted(split_counts.items())),
        "source_problem_ids": [source.source_problem_id for source in sources],
        "record_ids": [record.record_id for record in records],
        "fingerprint": fingerprint,
    }
    return ArcAdapterResult(
        metadata=pinned_metadata,
        sources=sources,
        records=records,
        slice_manifest=manifest,
    )


def write_slice_manifest(result: ArcAdapterResult, path: str | Path) -> Path:
    """Write only the small pinned manifest, never the retrieved dataset cache."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result.slice_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination


def build_arc_records(
    rows: Sequence[Mapping[str, Any]],
    *,
    upstream_split: str,
    metadata: ArcSourceMetadata,
) -> list[JudgeRecord]:
    """Convenience API returning canonical pairwise records for one source split."""

    return [
        canonicalize_arc_row(row, upstream_split=upstream_split, metadata=metadata)[1]
        for row in rows
    ]


__all__ = [
    "ARC_CANONICALIZATION_VERSION",
    "ARC_CONFIG",
    "ARC_DATASET_ID",
    "ARC_LICENSE",
    "ARC_SPLIT_POLICY",
    "ArcAdapterConfig",
    "ArcAdapterResult",
    "ArcSourceMetadata",
    "build_arc_dataset",
    "build_arc_records",
    "canonicalize_arc_row",
    "fingerprint_arc_output",
    "load_arc_rows",
    "map_arc_split",
    "normalize_license",
    "resolve_arc_source_metadata",
    "write_slice_manifest",
]
