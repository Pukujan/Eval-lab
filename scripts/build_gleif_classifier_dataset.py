"""Build the EXP-032 GLEIF closed-set classifier dataset and blind request pool.

Reads the frozen 2026-09-24 GLEIF snapshot from the local archive cache, samples
entities deterministically on an entity-disjoint split, and emits one single-mode
``JudgeRecord`` per (entity, family) whose gold label is the frozen source field
value. The provider request carries a masked record (the target field is removed
from the context) plus the closed label set; the gold label never enters a
request. Nothing here calls a model.

The label sets for ``entity-category`` and ``registration-status`` are the frozen
GLEIF CDF vocabularies declared at preregistration. ``legal-jurisdiction`` is
truncated to the top-N jurisdictions observed in the *public selection* half plus
an ``OTHER`` catch-all, so the vocabulary cannot leak blind-holdout composition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from eval_lab.datasets.gleif import (
    CLASSIFIER_FAMILIES,
    CLASSIFIER_PROMPT_VERSION,
    CLASSIFIER_VERIFIER_ID,
    DATASET,
    GleifEntity,
    category_item,
    entity_split,
    iter_entities,
    jurisdiction_item,
    normalize_lei,
    status_item,
)
from eval_lab.datasets.multidomain import stable_rank
from eval_lab.schema import JudgeRecord, Split

try:
    from scripts.build_gleif_dataset import (
        COLUMN_CANDIDATES,
        _read_header,
        _resolve_columns,
    )
    from scripts.freeze_gleif_snapshot import default_cache_dir
except ImportError:  # executed as a file from the repository root
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.build_gleif_dataset import (
        COLUMN_CANDIDATES,
        _read_header,
        _resolve_columns,
    )
    from scripts.freeze_gleif_snapshot import default_cache_dir

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = ROOT / "experiments" / "EXP-20261005-032-gleif-classifier"
# The frozen snapshot manifest is owned by EXP-026; EXP-032 reads it read-only and
# records its hash so the shared source revision stays auditable.
FROZEN_PATH = (
    ROOT / "experiments" / "EXP-20260922-026-gleif-objective-track" / "frozen-snapshot.json"
)
EXPERIMENT_ID = "EXP-20261005-032-gleif-classifier"
SEED = 260922
CONTEXT_LIMIT = 4096
ENTITY_TARGET = 1400
SELECT_RATIO = 0.0006
JURISDICTION_TOP_N = 20
OTHER_LABEL = "OTHER"
PRIMARY_PARTITION = "blind_holdout"
PARTITION_FOR_SPLIT = {Split.CALIBRATION: "public_selection", Split.TEST: "blind_holdout"}

CATEGORY_LABELS = (
    "GENERAL",
    "FUND",
    "SOLE_PROPRIETOR",
    "RESIDENT_GOVERNMENT_ENTITY",
    "BRANCH",
    "INTERNATIONAL_ORGANIZATION",
)
STATUS_LABELS = (
    "ISSUED",
    "LAPSED",
    "RETIRED",
    "DUPLICATE",
    "ANNULLED",
    "PENDING_TRANSFER",
    "PENDING_ARCHIVAL",
)

CATEGORY_CRITERIA = {
    "GENERAL": "A general legal entity that is not one of the other categories.",
    "FUND": "A collective investment vehicle or fund.",
    "SOLE_PROPRIETOR": "A natural person acting as a sole proprietor.",
    "RESIDENT_GOVERNMENT_ENTITY": "A government entity resident in the jurisdiction.",
    "BRANCH": "A branch of a legal entity registered in another jurisdiction.",
    "INTERNATIONAL_ORGANIZATION": (
        "An international organization established by treaty or intergovernmental agreement."
    ),
}
STATUS_CRITERIA = {
    "ISSUED": "The LEI is currently issued and the registration is active.",
    "LAPSED": "The registration has lapsed and the LEI has not been renewed.",
    "RETIRED": "The LEI has been retired and is no longer in use.",
    "DUPLICATE": "The LEI is a duplicate of another record.",
    "ANNULLED": "The LEI has been annulled.",
    "PENDING_TRANSFER": "A transfer of the LEI to another LOU is pending.",
    "PENDING_ARCHIVAL": "The LEI is pending archival.",
}

MASKED_FIELD_LINE = {
    "entity-category": "Entity category:",
    "registration-status": "Registration status:",
    "legal-jurisdiction": "Legal jurisdiction:",
}
GOLD_FIELD = {
    "entity-category": "EntityCategory",
    "registration-status": "RegistrationStatus",
    "legal-jurisdiction": "LegalJurisdiction",
}


def _json_fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def _fingerprint_records(records: Sequence[JudgeRecord]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(record.model_dump_json().encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _select_entities(
    lei_csv: Path, columns: Mapping[str, str]
) -> tuple[list[GleifEntity], Counter[str], Counter[str], int]:
    """One streaming pass: rank-select entities and census the controlled fields."""

    candidates: list[tuple[str, GleifEntity]] = []
    seen: set[str] = set()
    category_census: Counter[str] = Counter()
    status_census: Counter[str] = Counter()
    scanned = 0
    for entity in iter_entities(lei_csv, columns=columns):
        scanned += 1
        category_census[entity.entity_category.strip()] += 1
        status_census[entity.registration_status.strip()] += 1
        lei = normalize_lei(entity.lei)
        rank = stable_rank(SEED, "gleif-classifier-entity", lei)
        if int(rank[:16], 16) / float(16**16) < SELECT_RATIO and lei not in seen:
            seen.add(lei)
            candidates.append((rank, entity))
    candidates.sort(key=lambda item: item[0])
    if len(candidates) < ENTITY_TARGET:
        raise ValueError(
            f"rank selection produced {len(candidates)} candidates below target {ENTITY_TARGET}"
        )
    return (
        [entity for _, entity in candidates[:ENTITY_TARGET]],
        category_census,
        status_census,
        scanned,
    )


def _jurisdiction_vocabulary(public_entities: Sequence[GleifEntity]) -> list[str]:
    """Top-N jurisdictions in the public selection half, plus the OTHER catch-all."""

    counts = Counter(
        entity.legal_jurisdiction.strip().upper()
        for entity in public_entities
        if entity.legal_jurisdiction.strip()
    )
    if len(counts) < JURISDICTION_TOP_N:
        raise ValueError(
            f"public selection has only {len(counts)} jurisdictions, below top-N {JURISDICTION_TOP_N}"
        )
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [value for value, _ in ranked[:JURISDICTION_TOP_N]] + [OTHER_LABEL]


def build(cache_dir: Path) -> dict[str, Any]:
    frozen = json.loads(FROZEN_PATH.read_text(encoding="utf-8"))
    lei_entry = next(
        item for item in frozen["files"] if item["name"].startswith("20260924-0000-lei2")
    )
    lei_csv = cache_dir / lei_entry["csv_name"]
    if not lei_csv.is_file():
        raise FileNotFoundError(f"frozen CSV not found: {lei_csv}")

    header = _read_header(lei_csv)
    columns = _resolve_columns(header, COLUMN_CANDIDATES)
    entities, category_census, status_census, scanned = _select_entities(lei_csv, columns)

    observed_categories = {value for value in category_census if value}
    observed_statuses = {value for value in status_census if value}
    unexpected_categories = sorted(observed_categories - set(CATEGORY_LABELS))
    unexpected_statuses = sorted(observed_statuses - set(STATUS_LABELS))
    if unexpected_categories or unexpected_statuses:
        raise ValueError(
            "observed controlled values fall outside the preregistered label sets: "
            f"categories={unexpected_categories} statuses={unexpected_statuses}"
        )

    by_split: dict[Split, list[GleifEntity]] = {split: [] for split in Split}
    for entity in entities:
        by_split[entity_split(entity.lei, seed=SEED)].append(entity)
    jurisdiction_labels = _jurisdiction_vocabulary(by_split[Split.CALIBRATION])
    vocabularies: dict[str, list[str]] = {
        "entity-category": list(CATEGORY_LABELS),
        "registration-status": list(STATUS_LABELS),
        "legal-jurisdiction": jurisdiction_labels,
    }
    criteria: dict[str, dict[str, str]] = {
        "entity-category": CATEGORY_CRITERIA,
        "registration-status": STATUS_CRITERIA,
        "legal-jurisdiction": {
            label: (
                f"The jurisdiction is {label}."
                if label != OTHER_LABEL
                else "The jurisdiction is not one of the listed options."
            )
            for label in jurisdiction_labels
        },
    }

    records: list[JudgeRecord] = []
    skipped: Counter[str] = Counter()
    for entity in entities:
        item_builders = {
            "entity-category": category_item,
            "registration-status": status_item,
            "legal-jurisdiction": jurisdiction_item,
        }
        for family, builder in item_builders.items():
            try:
                records.append(builder(entity, vocabulary=vocabularies[family], seed=SEED))
            except ValueError:
                skipped[family] += 1

    records.sort(key=lambda record: record.record_id)
    record_ids = [record.record_id for record in records]
    duplicates = sorted({rid for rid, count in Counter(record_ids).items() if count > 1})
    if duplicates:
        raise ValueError(f"duplicate record IDs in the canonical dataset: {duplicates[:5]}")

    for record in records:
        family = record.perturbation["family"]
        marker = f"\n{MASKED_FIELD_LINE[family]} "
        if marker in record.prompt:
            raise ValueError(f"{record.record_id}: masked target field leaked into the prompt")
        if record.candidate_a and record.gold.label in record.candidate_a:
            raise ValueError(f"{record.record_id}: gold label leaked into the candidate")

    entities_by_split: dict[str, set[str]] = {"calibration": set(), "test": set()}
    for record in records:
        entities_by_split[record.split.value].add(record.gold.evidence["entity_lei"])
    overlap = entities_by_split["calibration"] & entities_by_split["test"]
    if overlap:
        raise ValueError(f"entity split is not disjoint: {sorted(overlap)[:5]}")

    split_counts = Counter(record.split for record in records)
    blind_records = [record for record in records if record.split is Split.TEST]

    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    (EXPERIMENT_DIR / "canonical-records.jsonl").write_text(
        "".join(record.model_dump_json() + "\n" for record in records), encoding="utf-8"
    )

    split_manifest = {
        "experiment_id": EXPERIMENT_ID,
        "seed": SEED,
        "split_policy": (
            "entity-disjoint calibration/test on normalized LEI; all families for one entity "
            "share its split"
        ),
        "entity_count": len(entities),
        "entities_scanned": scanned,
        "record_counts": {split.value: split_counts[split] for split in Split},
        "entity_counts": {name: len(members) for name, members in entities_by_split.items()},
        "families": list(CLASSIFIER_FAMILIES),
        "record_ids_fingerprint": _json_fingerprint(record_ids),
        "blind_record_ids_fingerprint": _json_fingerprint(
            sorted(record.record_id for record in blind_records)
        ),
    }
    (EXPERIMENT_DIR / "split-manifest.json").write_text(
        json.dumps(split_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    rows = [
        {
            "dataset": DATASET,
            "family": record.perturbation["family"],
            "partition": PARTITION_FOR_SPLIT[record.split],
            "record": record.model_dump(mode="json"),
            "source_problem_id": record.source_problem_id,
            "source_revision": frozen["snapshot_date"],
        }
        for record in records
    ]
    (EXPERIMENT_DIR / "records.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )

    typed_spec = {
        "spec_id": "gleif-registry-classification",
        "spec_version": CLASSIFIER_PROMPT_VERSION,
        "base_spec_id": "eval-lab-system-one",
        "base_spec_version": "0.1.0",
        "question_type": "choice",
        "context_limit": CONTEXT_LIMIT,
        "confidence_definition": (
            "native normalized provider probabilities only; label-only responses have no "
            "confidence metric"
        ),
        "families": {
            family: {
                "legal_labels": vocabularies[family],
                "criteria": {label: criteria[family][label] for label in vocabularies[family]},
                "masked_field": MASKED_FIELD_LINE[family].rstrip(":"),
                "gold_field": GOLD_FIELD[family],
                "verifier_id": CLASSIFIER_VERIFIER_ID,
            }
            for family in CLASSIFIER_FAMILIES
        },
        "target_error_rates": [0.01, 0.02, 0.05],
    }
    (EXPERIMENT_DIR / "typed-question-spec.json").write_text(
        json.dumps(typed_spec, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    requests_dir = EXPERIMENT_DIR / "requests"
    requests_dir.mkdir(parents=True, exist_ok=True)
    for family in CLASSIFIER_FAMILIES:
        family_records = [
            record for record in blind_records if record.perturbation["family"] == family
        ]
        payload = [
            {
                "record_id": record.record_id,
                "source_problem_id": record.source_problem_id,
                "mode": record.mode.value,
                "prompt": record.prompt,
                "candidate_a": record.candidate_a,
                "legal_labels": vocabularies[family],
                "criteria": {label: criteria[family][label] for label in vocabularies[family]},
            }
            for record in family_records
        ]
        (requests_dir / f"{family}.jsonl").write_text(
            "".join(json.dumps(item, sort_keys=True) + "\n" for item in payload), encoding="utf-8"
        )

    pool_manifest = {
        "experiment_id": EXPERIMENT_ID,
        "frozen_at_utc": frozen["frozen_at_utc"],
        "source_files": [item["csv_name"] for item in frozen["files"]],
        "frozen_snapshot_path": FROZEN_PATH.relative_to(ROOT).as_posix(),
        "frozen_snapshot_sha256": hashlib.sha256(FROZEN_PATH.read_bytes()).hexdigest(),
        "source_file_sha256": {item["csv_name"]: item["sha256"] for item in frozen["files"]},
        "record_count": len(records),
        "partition_counts": dict(sorted(Counter(row["partition"] for row in rows).items())),
        "family_counts": dict(sorted(Counter(row["family"] for row in rows).items())),
        "blind_record_counts": dict(
            sorted(Counter(record.perturbation["family"] for record in blind_records).items())
        ),
        "source_problem_id_count": len({record.source_problem_id for record in records}),
        "records_fingerprint": _fingerprint_records(records),
        "blind_record_ids_fingerprint": split_manifest["blind_record_ids_fingerprint"],
        "typed_question_spec_fingerprint": _json_fingerprint(typed_spec),
        "typed_spec_id": typed_spec["spec_id"],
        "typed_spec_version": typed_spec["spec_version"],
        "primary_partition": PRIMARY_PARTITION,
        "gold_provenance": sorted({record.gold.provenance.value for record in records}),
        "verifier_id": CLASSIFIER_VERIFIER_ID,
        "label_sets": {family: vocabularies[family] for family in CLASSIFIER_FAMILIES},
        "label_sets_fingerprint": _json_fingerprint(
            {family: vocabularies[family] for family in CLASSIFIER_FAMILIES}
        ),
        "sampled_label_support": {
            "entity-category": {label: category_census[label] for label in CATEGORY_LABELS},
            "registration-status": {label: status_census[label] for label in STATUS_LABELS},
        },
        "snapshot_field_census": {
            "entity-category": dict(sorted(category_census.items())),
            "registration-status": dict(sorted(status_census.items())),
        },
        "skipped_items": dict(sorted(skipped.items())),
        "status": "frozen_before_blind_evaluation",
    }
    (EXPERIMENT_DIR / "pool-manifest.json").write_text(
        json.dumps(pool_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    checksums = []
    for path in sorted(
        [
            *EXPERIMENT_DIR.glob("*.json"),
            *EXPERIMENT_DIR.glob("*.jsonl"),
            *requests_dir.glob("*.jsonl"),
        ]
    ):
        if path.name == "pool-checksums.sha256":
            continue
        checksums.append(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(EXPERIMENT_DIR).as_posix()}"
        )
    (EXPERIMENT_DIR / "pool-checksums.sha256").write_text(
        "\n".join(checksums) + "\n", encoding="utf-8"
    )

    canonical_sha = hashlib.sha256(
        (EXPERIMENT_DIR / "canonical-records.jsonl").read_bytes()
    ).hexdigest()
    return pool_manifest | {
        "canonical_dataset_sha256": canonical_sha,
        "entity_count": len(entities),
        "entities_scanned": scanned,
        "jurisdiction_labels": jurisdiction_labels,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(os.environ["GLEIF_CACHE_DIR"]) if os.environ.get("GLEIF_CACHE_DIR") else None,
    )
    args = parser.parse_args()
    cache_dir = args.cache_dir if args.cache_dir is not None else default_cache_dir()
    try:
        summary = build(cache_dir)
    except (OSError, ValueError) as exc:
        print(f"GLEIF classifier build stopped: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
