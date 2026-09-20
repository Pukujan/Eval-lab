import json

import pytest

from eval_lab.datasets.arc import (
    ARC_LICENSE,
    ArcAdapterConfig,
    build_arc_dataset,
    canonicalize_arc_row,
    map_arc_split,
    resolve_arc_source_metadata,
    write_slice_manifest,
)
from eval_lab.schema import (
    GoldProvenance,
    JudgmentMode,
    Split,
)

MOCK_METADATA = {
    "sha": "0123456789abcdef0123456789abcdef01234567",
    "cardData": {"license": "cc-by-sa-4.0"},
}


def _metadata():
    return resolve_arc_source_metadata(payload=MOCK_METADATA)


def _row(row_id: str = "arc-1") -> dict[str, object]:
    return {
        "id": row_id,
        "question": "Which material conducts electricity?",
        "choices": {
            "label": ["A", "B", "C", "D"],
            "text": ["wood", "copper", "glass", "rubber"],
        },
        "answerKey": "B",
    }


def test_metadata_resolution_pins_revision_and_license() -> None:
    metadata = resolve_arc_source_metadata(
        ArcAdapterConfig(requested_revision="main"),
        payload=MOCK_METADATA,
    )

    assert metadata.resolved_revision == MOCK_METADATA["sha"]
    assert metadata.license == ARC_LICENSE
    assert metadata.requested_revision == "main"


def test_canonical_row_preserves_id_answer_provenance_and_pairwise_candidates() -> None:
    source, record = canonicalize_arc_row(_row(), upstream_split="validation", metadata=_metadata())

    assert source.source_problem_id == "arc-1"
    assert source.reference_answer["answer_key"] == "B"
    assert record.source_problem_id == "arc-1"
    assert record.mode is JudgmentMode.PAIRWISE
    assert record.gold.provenance is GoldProvenance.ANSWER_KEY
    assert record.candidate_a != record.candidate_b
    assert "Which material conducts electricity?" in record.prompt
    assert record.split in {Split.DEV, Split.CALIBRATION}


def test_validation_mapping_is_deterministic_and_split_safe() -> None:
    first = map_arc_split("validation", "arc-1", seed=17)
    second = map_arc_split("validation", "arc-1", seed=17)

    assert first is second
    assert map_arc_split("train", "arc-1") is Split.TRAIN
    assert map_arc_split("test", "arc-1") is Split.TEST
    assert map_arc_split("validation", "arc-1", seed=17) == map_arc_split("validation", "arc-1", seed=17)


def test_fingerprint_and_manifest_are_stable_and_serializable(tmp_path) -> None:
    rows = {"validation": [_row("arc-1"), _row("arc-2")]}
    first = build_arc_dataset(rows, metadata=_metadata())
    second = build_arc_dataset(rows, metadata=_metadata())
    path = write_slice_manifest(first, tmp_path / "arc-slice.json")

    assert first.fingerprint == second.fingerprint
    assert first.slice_manifest["resolved_revision"] == MOCK_METADATA["sha"]
    assert first.slice_manifest["split_policy"]["validation"] == "dev_or_calibration_by_source_id"
    assert first.slice_manifest["validation_dev_fraction"] == 0.5
    assert json.loads(path.read_text(encoding="utf-8"))["fingerprint"] == first.fingerprint
    assert first.metadata.model_validate_json(first.metadata.model_dump_json()) == first.metadata

    changed_revision = _metadata().model_copy(update={"resolved_revision": "fedcba9876543210"})
    assert build_arc_dataset(rows, metadata=changed_revision).fingerprint != first.fingerprint


def test_license_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="expected ARC license"):
        resolve_arc_source_metadata(payload={"sha": "abc", "cardData": {"license": "mit"}})
