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
    "ArcAdapterConfig",
    "ArcAdapterResult",
    "ArcSourceMetadata",
    "SyntheticFixture",
    "assign_split",
    "build_arc_dataset",
    "build_arc_records",
    "build_synthetic_fixture",
    "canonicalize_arc_row",
    "generate_synthetic_fixtures",
    "map_arc_split",
    "resolve_arc_source_metadata",
    "serialize_fixture",
    "split_for_source",
    "write_slice_manifest",
]
