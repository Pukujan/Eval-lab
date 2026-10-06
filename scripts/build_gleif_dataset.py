"""Build the EXP-026 GLEIF canonical dataset and frozen comparison pool.

Reads the frozen snapshot recorded by ``scripts/freeze_gleif_snapshot.py`` from
the local archive cache, samples entities and relationships deterministically,
emits objective claim-verification pairs, and writes the canonical dataset, the
entity-disjoint split manifest, and the pool the shared comparison runner
consumes. Nothing here calls a model; scoring the blind partition is a separate,
later step gated by the EXP-026 stopping rule.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from eval_lab.datasets.gleif import (
    DATASET,
    PROMPT_VERSION,
    SPLIT_FAMILY,
    VERIFIER_ID,
    GleifEntity,
    category_claims,
    iter_entities,
    jurisdiction_claims,
    parent_claims,
    registration_date_claims,
    status_claims,
)
from eval_lab.datasets.multidomain import stable_rank
from eval_lab.schema import JudgeRecord, Split

try:
    from scripts.freeze_gleif_snapshot import default_cache_dir
except ImportError:  # executed as a file from the repository root
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.freeze_gleif_snapshot import default_cache_dir

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = ROOT / "experiments" / "EXP-20260922-026-gleif-objective-track"
FROZEN_PATH = EXPERIMENT_DIR / "frozen-snapshot.json"
SOURCE_MANIFEST_PATH = EXPERIMENT_DIR / "source-manifest.json"
EXPERIMENT_ID = "EXP-20260922-026-gleif-objective-track"
SEED = 260922
CONTEXT_LIMIT = 4096
ENTITY_TARGET = 300
RELATIONSHIP_TARGET = 60
SELECT_RATIO = 0.002
PRIMARY_PARTITION = "blind_holdout"
PARTITION_FOR_SPLIT = {Split.CALIBRATION: "public_selection", Split.TEST: "blind_holdout"}

COLUMN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "lei": ("LEI",),
    "legal_name": ("Entity.LegalName", "Entity.LegalName.1", "LegalName"),
    "entity_category": ("Entity.EntityCategory", "EntityCategory"),
    "legal_jurisdiction": ("Entity.LegalJurisdiction", "Entity.LegalJurisdiction.1"),
    "registration_status": ("Registration.RegistrationStatus", "RegistrationStatus"),
    "initial_registration_date": (
        "Registration.InitialRegistrationDate",
        "InitialRegistrationDate",
    ),
}
RR_COLUMN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "start": ("Relationship.StartNode.NodeID",),
    "end": ("Relationship.EndNode.NodeID",),
    "type": ("Relationship.RelationshipType",),
    "status": ("Relationship.RelationshipStatus",),
}


def _resolve_columns(
    header: Sequence[str], candidates: Mapping[str, Sequence[str]]
) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for logical, options in candidates.items():
        for option in options:
            if option in header:
                resolved[logical] = option
                break
        else:
            raise ValueError(f"none of {list(options)} present in header for {logical!r}")
    return resolved


def _fingerprint_records(records: Sequence[JudgeRecord]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(record.model_dump_json().encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _json_fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def _read_header(csv_path: Path) -> list[str]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        return next(csv.reader(stream))


def _sample_relationships(rr_csv: Path) -> list[dict[str, str]]:
    header = _read_header(rr_csv)
    columns = _resolve_columns(header, RR_COLUMN_CANDIDATES)
    index = {logical: header.index(actual) for logical, actual in columns.items()}
    ranked: list[tuple[str, dict[str, str]]] = []
    seen: set[tuple[str, str, str]] = set()
    with rr_csv.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        next(reader)
        for row in reader:
            if len(row) != len(header):
                continue
            start = row[index["start"]].strip().upper()
            end = row[index["end"]].strip().upper()
            if len(start) != 20 or len(end) != 20 or start == end:
                continue
            relationship_type = row[index["type"]].strip()
            key = (start, end, relationship_type)
            if key in seen:
                continue
            rank = stable_rank(SEED, "gleif-parent", f"{start}:{end}:{relationship_type}")
            if int(rank[:16], 16) / float(16**16) < SELECT_RATIO:
                seen.add(key)
                ranked.append(
                    (
                        rank,
                        {
                            "start": start,
                            "end": end,
                            "type": relationship_type,
                            "status": row[index["status"]].strip(),
                        },
                    )
                )
    ranked.sort(key=lambda item: item[0])
    selected: list[dict[str, str]] = []
    seen_starts: set[str] = set()
    for _, relationship in ranked:
        if relationship["start"] in seen_starts:
            continue
        seen_starts.add(relationship["start"])
        selected.append(relationship)
        if len(selected) >= RELATIONSHIP_TARGET:
            break
    return selected


def _entity_vocabularies(entities: Sequence[GleifEntity]) -> dict[str, list[str]]:
    return {
        "status": sorted(
            {entity.registration_status for entity in entities if entity.registration_status}
        ),
        "jurisdiction": sorted(
            {entity.legal_jurisdiction for entity in entities if entity.legal_jurisdiction}
        ),
        "category": sorted(
            {entity.entity_category for entity in entities if entity.entity_category}
        ),
    }


def build(cache_dir: Path) -> dict[str, Any]:
    frozen = json.loads(FROZEN_PATH.read_text(encoding="utf-8"))
    lei_entry = next(
        item for item in frozen["files"] if item["name"].startswith("20260924-0000-lei2")
    )
    rr_entry = next(item for item in frozen["files"] if item["name"].startswith("20260924-0000-rr"))
    lei_csv = cache_dir / lei_entry["csv_name"]
    rr_csv = cache_dir / rr_entry["csv_name"]
    for path in (lei_csv, rr_csv):
        if not path.is_file():
            raise FileNotFoundError(f"frozen CSV not found: {path}")

    header = _read_header(lei_csv)
    columns = _resolve_columns(header, COLUMN_CANDIDATES)

    relationships = _sample_relationships(rr_csv)
    needed_names = {relationship["start"] for relationship in relationships}

    candidates: list[tuple[str, GleifEntity]] = []
    names: dict[str, str] = {}
    seen_candidates: set[str] = set()
    for entity in iter_entities(lei_csv, columns=columns):
        lei = entity.lei.strip().upper()
        rank = stable_rank(SEED, "gleif-entity", lei)
        if int(rank[:16], 16) / float(16**16) < SELECT_RATIO and lei not in seen_candidates:
            seen_candidates.add(lei)
            candidates.append((rank, entity))
        if lei in needed_names:
            names[lei] = entity.legal_name
    candidates.sort(key=lambda item: item[0])
    if len(candidates) < ENTITY_TARGET:
        raise ValueError(f"selected {len(candidates)} entities below target {ENTITY_TARGET}")
    entities = [entity for _, entity in candidates[:ENTITY_TARGET]]

    vocab = _entity_vocabularies(entities)

    records: list[JudgeRecord] = []
    for entity in entities:
        records.extend(status_claims(entity, status_vocabulary=vocab["status"], seed=SEED))
        records.extend(
            jurisdiction_claims(entity, jurisdiction_vocabulary=vocab["jurisdiction"], seed=SEED)
        )
        records.extend(category_claims(entity, category_vocabulary=vocab["category"], seed=SEED))
        records.extend(registration_date_claims(entity, seed=SEED))

    wanted = [entity.lei.strip().upper() for entity in entities]
    for relationship in relationships:
        start, end = relationship["start"], relationship["end"]
        start_name = names.get(start, start)
        distractor = next(
            (lei for lei in wanted if lei not in {start, end}),
            None,
        )
        if distractor is None:
            continue
        records.extend(
            parent_claims(
                start_lei=start,
                start_name=start_name,
                parent_lei=end,
                wrong_lei=distractor,
                relationship_type=relationship["type"],
                seed=SEED,
            )
        )

    records.sort(key=lambda record: record.record_id)
    record_ids = [record.record_id for record in records]
    duplicates = sorted({rid for rid, count in Counter(record_ids).items() if count > 1})
    if duplicates:
        raise ValueError(f"duplicate record IDs in the canonical dataset: {duplicates[:5]}")

    split_counts = Counter(record.split for record in records)
    entities_by_split: dict[str, set[str]] = {"calibration": set(), "test": set()}
    for record in records:
        entities_by_split[record.split.value].add(record.gold.evidence["entity_lei"])
    overlap = entities_by_split["calibration"] & entities_by_split["test"]
    if overlap:
        raise ValueError(f"entity split is not disjoint: {sorted(overlap)[:5]}")

    (EXPERIMENT_DIR / "canonical-records.jsonl").write_text(
        "".join(record.model_dump_json() + "\n" for record in records), encoding="utf-8"
    )

    split_manifest = {
        "experiment_id": EXPERIMENT_ID,
        "seed": SEED,
        "split_policy": "entity-disjoint calibration/test on normalized LEI",
        "split_family": SPLIT_FAMILY,
        "entity_count": len(entities),
        "record_counts": {split.value: split_counts[split] for split in Split},
        "entity_counts": {name: len(members) for name, members in entities_by_split.items()},
        "record_ids_fingerprint": _json_fingerprint(record_ids),
    }
    (EXPERIMENT_DIR / "split-manifest.json").write_text(
        json.dumps(split_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    rows = [
        {
            "dataset": DATASET,
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
        "confidence_definition": "native normalized provider probabilities only; label-only responses have no confidence metric",
        "context_limit": CONTEXT_LIMIT,
        "pairwise_legal_labels": ["A", "B", "TIE"],
        "question_type": "choice",
        "single_legal_labels": ["pass", "fail"],
        "spec_id": "gleif-registry-facts",
        "spec_version": PROMPT_VERSION,
        "target_error_rates": [0.01, 0.02, 0.05],
    }
    (EXPERIMENT_DIR / "typed-question-spec.json").write_text(
        json.dumps(typed_spec, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    blind_ids = sorted(record.record_id for record in records if record.split is Split.TEST)
    pool_manifest = {
        "experiment_id": EXPERIMENT_ID,
        "source_experiment": EXPERIMENT_ID,
        "frozen_at_utc": frozen["frozen_at_utc"],
        "source_files": [item["csv_name"] for item in frozen["files"]],
        "record_count": len(records),
        "partition_counts": dict(sorted(Counter(row["partition"] for row in rows).items())),
        "source_problem_id_count": len({record.source_problem_id for record in records}),
        "records_fingerprint": _fingerprint_records(records),
        "blind_record_ids_fingerprint": _json_fingerprint(blind_ids),
        "typed_question_spec_fingerprint": _json_fingerprint(typed_spec),
        "typed_spec_id": typed_spec["spec_id"],
        "typed_spec_version": typed_spec["spec_version"],
        "primary_partition": PRIMARY_PARTITION,
        "gold_provenance": sorted({record.gold.provenance.value for record in records}),
        "verifier_id": VERIFIER_ID,
        "status": "frozen_before_blind_evaluation",
    }
    (EXPERIMENT_DIR / "pool-manifest.json").write_text(
        json.dumps(pool_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    checksums = []
    for name in sorted(
        (
            "canonical-records.jsonl",
            "records.jsonl",
            "split-manifest.json",
            "typed-question-spec.json",
            "pool-manifest.json",
        )
    ):
        path = EXPERIMENT_DIR / name
        checksums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {name}")
    (EXPERIMENT_DIR / "pool-checksums.sha256").write_text(
        "\n".join(checksums) + "\n", encoding="utf-8"
    )

    canonical_sha = hashlib.sha256(
        (EXPERIMENT_DIR / "canonical-records.jsonl").read_bytes()
    ).hexdigest()
    source_manifest = json.loads(SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    source_manifest["canonical_dataset_sha256"] = canonical_sha
    SOURCE_MANIFEST_PATH.write_text(json.dumps(source_manifest, indent=2) + "\n", encoding="utf-8")

    return pool_manifest | {"canonical_dataset_sha256": canonical_sha}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(os.environ.get("GLEIF_CACHE_DIR", ""))
        if os.environ.get("GLEIF_CACHE_DIR")
        else None,
    )
    args = parser.parse_args()
    cache_dir = args.cache_dir
    if cache_dir is None:
        cache_dir = default_cache_dir()
    try:
        summary = build(cache_dir)
    except (OSError, ValueError) as exc:
        print(f"GLEIF build stopped: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
