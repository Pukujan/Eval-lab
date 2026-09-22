"""Dataset builders and deterministic fixture utilities."""

from eval_lab.datasets.arc import (
    ArcAdapterConfig,
    ArcAdapterResult,
    ArcSourceMetadata,
    build_arc_dataset,
    build_arc_records,
    canonicalize_arc_row,
    map_arc_split,
    resolve_arc_source_metadata,
    write_slice_manifest,
)
from eval_lab.datasets.selective import (
    SELECTIVE_CANONICALIZATION_VERSION,
    SELECTIVE_DATASET_ID,
    arc_single_records,
    combine_selective_records,
    partition_records,
)
from eval_lab.datasets.synthetic import (
    DEFAULT_SPLIT_SEED,
    SyntheticFixture,
    assign_split,
    build_synthetic_fixture,
    generate_synthetic_fixtures,
    serialize_fixture,
    split_for_source,
)

__all__ = [
    "DEFAULT_SPLIT_SEED",
    "SELECTIVE_CANONICALIZATION_VERSION",
    "SELECTIVE_DATASET_ID",
    "ArcAdapterConfig",
    "ArcAdapterResult",
    "ArcSourceMetadata",
    "SyntheticFixture",
    "arc_single_records",
    "assign_split",
    "build_arc_dataset",
    "build_arc_records",
    "build_synthetic_fixture",
    "canonicalize_arc_row",
    "combine_selective_records",
    "generate_synthetic_fixtures",
    "map_arc_split",
    "partition_records",
    "resolve_arc_source_metadata",
    "serialize_fixture",
    "split_for_source",
    "write_slice_manifest",
]
