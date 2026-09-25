"""SQLAlchemy models for the live read model.

Two schemas, matching the architecture doc (``docs/architecture/live-app.md``
section 5):

``live``
    Everything safe to serve publicly.  It holds **no** per-record data: no
    record text, no prompts, no gold labels, no per-record labels.  The public
    API role has ``SELECT`` here and nothing else.
``private``
    Per-record tables used for recompute and audits only (``predictions``) plus
    operational secrets (``runner_tokens``).  The public API role has no grant on
    this schema at all, which is the leakage backstop tested in
    ``live/tests/test_roles_pg.py``.

The models are portable: ``JSON`` on SQLite for the unit tests, ``JSONB`` on
Postgres.  Tests attach ``schema_translate_map={"live": None, "private": None}``
so the same tables work on SQLite; production always uses the real schemas.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SCHEMA_LIVE = "live"
SCHEMA_PRIVATE = "private"

#: ``JSONB`` on Postgres, plain ``JSON`` everywhere else (the SQLite test path).
JSONType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(UTC)


class LiveBase(DeclarativeBase):
    """Base for the publicly readable schema.

    Every table in this metadata is created inside the ``live`` schema, which is
    the only schema the public API role can read.
    """

    metadata = MetaData(schema=SCHEMA_LIVE)


class PrivateBase(DeclarativeBase):
    """Base for the never-served schema."""

    metadata = MetaData(schema=SCHEMA_PRIVATE)


class Project(LiveBase):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Dataset(LiveBase):
    """A frozen evaluation population (the 760-record blind holdout here).

    ``title``/``description``/``population``/``notes`` are the dataset-level
    extras of a chart-data v1 document that do not belong in a tidy table; they
    are stored as JSON so the API can rebuild the document byte-for-byte.
    """

    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("live.projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    records_fingerprint: Mapped[str | None] = mapped_column(String(64))
    blind_ids_fingerprint: Mapped[str | None] = mapped_column(String(64))
    spec_fingerprint: Mapped[str | None] = mapped_column(String(64))
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    public_count: Mapped[int] = mapped_column(Integer, default=0)
    blind_count: Mapped[int] = mapped_column(Integer, default=0)
    #: Overrides ``Settings.min_slice_records`` for this dataset.  ``None`` means
    #: "use the configured threshold".  It is set to 0 only for a dataset whose
    #: records and gold labels are already in the public repository, where the
    #: rule would hide numbers the papers publish.
    min_slice_records: Mapped[int | None] = mapped_column(Integer)
    split_policy: Mapped[str | None] = mapped_column(Text)
    canonical_id: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    experiment_id: Mapped[str | None] = mapped_column(String(64))
    population: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    notes: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    provenance: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Experiment(LiveBase):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("live.projects.id", ondelete="CASCADE"))
    short_id: Mapped[str] = mapped_column(String(16), index=True)
    title: Mapped[str | None] = mapped_column(Text)
    hypothesis: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(64))
    code_commit: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[str | None] = mapped_column(String(64))
    directory: Mapped[str] = mapped_column(Text)
    manifest: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    position: Mapped[int] = mapped_column(Integer, default=0)


class Judge(LiveBase):
    __tablename__ = "judges"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("live.projects.id", ondelete="CASCADE"))
    provider: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(200))
    route: Mapped[str | None] = mapped_column(Text)
    family: Mapped[str | None] = mapped_column(String(64))
    params_b: Mapped[float | None] = mapped_column(Float)
    deployment: Mapped[str] = mapped_column(String(32), default="api")
    short_label: Mapped[str | None] = mapped_column(String(64))


class Arm(LiveBase):
    """One judge configuration = one chart-data v1 *entity*."""

    __tablename__ = "arms"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("live.datasets.id", ondelete="CASCADE"))
    experiment_id: Mapped[str] = mapped_column(ForeignKey("live.experiments.id"))
    judge_id: Mapped[str] = mapped_column(ForeignKey("live.judges.id"))
    label: Mapped[str] = mapped_column(Text)
    short_label: Mapped[str] = mapped_column(String(64))
    headline: Mapped[bool] = mapped_column(Boolean, default=False)
    experiment: Mapped[str] = mapped_column(String(64))
    experiment_ids: Mapped[list[str]] = mapped_column(JSONType, default=list)
    deployment: Mapped[str] = mapped_column(String(32))
    model_family: Mapped[str | None] = mapped_column(String(64))
    model_id: Mapped[str | None] = mapped_column(String(200))
    params_b: Mapped[float | None] = mapped_column(Float)
    route: Mapped[str | None] = mapped_column(Text)
    harness: Mapped[str | None] = mapped_column(Text)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    config_hash: Mapped[str | None] = mapped_column(String(64))
    settings_evidence: Mapped[list[str] | None] = mapped_column(JSONType)
    derived: Mapped[bool] = mapped_column(Boolean, default=False)
    rank_all_record: Mapped[int | None] = mapped_column(Integer)
    shared_rank_all_record: Mapped[int | None] = mapped_column(Integer)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    resolved: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    status_counts: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    position: Mapped[int] = mapped_column(Integer, default=0)


class Run(LiveBase):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(300), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("live.datasets.id", ondelete="CASCADE"))
    experiment_id: Mapped[str] = mapped_column(ForeignKey("live.experiments.id"))
    #: The arm this run belongs to, when the run maps 1:1 onto a chart entity.
    #: Merged arms (declared merges) span several runs and leave this null; the
    #: ``run_entities`` association below carries the many-to-many mapping.
    arm_id: Mapped[str | None] = mapped_column(ForeignKey("live.arms.id"))
    partition: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    elapsed_s: Mapped[float | None] = mapped_column(Float)
    record_count: Mapped[int | None] = mapped_column(Integer)
    #: Largest per-arm resolved count in the file.  A single ``results.json`` can
    #: cover several judges (EXP-022 runs five in one directory), so there is no
    #: single "records resolved" number; ``arm_summary`` keeps them all.
    resolved_count: Mapped[int | None] = mapped_column(Integer)
    arm_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    status_counts: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    code_commit: Mapped[str | None] = mapped_column(String(64))
    tree_dirty: Mapped[bool | None] = mapped_column(Boolean)
    runner_host: Mapped[str | None] = mapped_column(String(200))
    git_committed: Mapped[bool] = mapped_column(Boolean, default=True)
    eval_lab_commit: Mapped[str | None] = mapped_column(String(64))
    visibility: Mapped[str] = mapped_column(String(32), default="public")
    ingest_id: Mapped[str | None] = mapped_column(String(64))
    results_path: Mapped[str | None] = mapped_column(Text)
    results_sha256: Mapped[str | None] = mapped_column(String(64))
    provider: Mapped[str | None] = mapped_column(String(64))
    requested_model: Mapped[str | None] = mapped_column(String(200))
    partition_fingerprints: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    execution: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    #: Position of this run inside its entity's ``runs`` array in the chart-data
    #: document (the exporter's ``mergeOrder``).
    position: Mapped[int] = mapped_column(Integer, default=0)


class RunEntity(LiveBase):
    """Which run artifacts feed which chart entity.

    A declared merge (``qwen_flash_exp015_016``) is one entity fed by two runs,
    so this is many-to-many.  ``artifact_path`` is the *prediction file* the run
    contributes (``.../predictions/grok.jsonl``), which is what a chart-data v1
    ``runs[]`` entry hashes -- not ``results.json``.
    """

    __tablename__ = "run_entities"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("live.runs.run_id", ondelete="CASCADE"), primary_key=True
    )
    entity_id: Mapped[str] = mapped_column(
        ForeignKey("live.arms.id", ondelete="CASCADE"), primary_key=True
    )
    merge_order: Mapped[int] = mapped_column(Integer, default=0)
    artifact_path: Mapped[str] = mapped_column(Text, primary_key=True)
    artifact_sha256: Mapped[str | None] = mapped_column(String(64))


class Metric(LiveBase):
    """The metric registry: a chart-data v1 *measure*."""

    __tablename__ = "metrics"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("live.projects.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(Text)
    unit: Mapped[str] = mapped_column(String(32))
    format: Mapped[str] = mapped_column(String(32))
    better: Mapped[str] = mapped_column(String(16))
    interval_method: Mapped[str] = mapped_column(String(32))
    definition: Mapped[str] = mapped_column(Text)
    n_label: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0)


class Dimension(LiveBase):
    """A chart-data v1 *dimension* (an entity or slice facet)."""

    __tablename__ = "dimensions"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("live.datasets.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(32))
    scope: Mapped[str] = mapped_column(String(16))
    field: Mapped[str | None] = mapped_column(String(64))
    unit: Mapped[str | None] = mapped_column(String(32))
    values: Mapped[list[str] | None] = mapped_column(JSONType)
    position: Mapped[int] = mapped_column(Integer, default=0)


class Level(LiveBase):
    """A chart-data v1 *level* (summary / breakdown / experiments / runs / table)."""

    __tablename__ = "levels"

    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("live.datasets.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0)


class Observation(LiveBase):
    """A tidy ``(entity, slice, metric) -> value/CI/n`` row.

    ``slice_records`` is the population of the slice (the denominator of
    ``all_record_accuracy``/``coverage``).  It is the number the min-slice rule
    looks at, and it is *not* part of the chart-data v1 observation, so it is
    never serialized.
    """

    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("live.datasets.id", ondelete="CASCADE"))
    entity_id: Mapped[str] = mapped_column(
        ForeignKey("live.arms.id", ondelete="CASCADE"), index=True
    )
    metric_key: Mapped[str] = mapped_column(ForeignKey("live.metrics.key"), index=True)
    slice_dim: Mapped[str] = mapped_column(String(32), index=True)
    slice_value: Mapped[str] = mapped_column(String(200))
    value: Mapped[float | None] = mapped_column(Float)
    ci_low: Mapped[float | None] = mapped_column(Float)
    ci_high: Mapped[float | None] = mapped_column(Float)
    n: Mapped[int] = mapped_column(Integer, default=0)
    slice_records: Mapped[int] = mapped_column(Integer, default=0)
    position: Mapped[int] = mapped_column(Integer, default=0)


class Aggregate(LiveBase):
    """A declared cross-run merge.  The browser never averages across arms."""

    __tablename__ = "aggregates"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("live.datasets.id", ondelete="CASCADE"))
    metric_key: Mapped[str] = mapped_column(String(64))
    method: Mapped[str] = mapped_column(Text)
    over: Mapped[str] = mapped_column(String(64))
    derived_from_run_ids: Mapped[list[str]] = mapped_column(JSONType, default=list)
    value: Mapped[float | None] = mapped_column(Float)
    ci_low: Mapped[float | None] = mapped_column(Float)
    ci_high: Mapped[float | None] = mapped_column(Float)
    n: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer, default=0)


class Comparison(LiveBase):
    """A paired test between two entities (McNemar, Holm-corrected)."""

    __tablename__ = "comparisons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("live.datasets.id", ondelete="CASCADE"))
    left: Mapped[str] = mapped_column(String(128))
    right: Mapped[str] = mapped_column(String(128))
    view: Mapped[str] = mapped_column(String(16))
    test: Mapped[str] = mapped_column(String(64), default="mcnemar_exact_two_sided")
    statistic: Mapped[float | None] = mapped_column(Float)
    p: Mapped[float | None] = mapped_column(Float)
    p_holm: Mapped[float | None] = mapped_column(Float)
    n: Mapped[int] = mapped_column(Integer, default=0)
    left_only_correct: Mapped[int] = mapped_column(Integer, default=0)
    right_only_correct: Mapped[int] = mapped_column(Integer, default=0)
    scope: Mapped[str | None] = mapped_column(String(64))
    position: Mapped[int] = mapped_column(Integer, default=0)


class Artifact(LiveBase):
    """A hashed file produced by a run (``checksums.sha256`` / results.json)."""

    __tablename__ = "artifacts"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("live.runs.run_id", ondelete="CASCADE"), primary_key=True
    )
    path: Mapped[str] = mapped_column(Text, primary_key=True)
    sha256: Mapped[str | None] = mapped_column(String(64))
    bytes: Mapped[int | None] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(32), default="file")


class Activity(LiveBase):
    """PROV-O activity, rendered as JSON-LD by ``/runs/{id}/provenance.jsonld``."""

    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    type: Mapped[str] = mapped_column(String(32))
    agent: Mapped[str | None] = mapped_column(String(200))
    software: Mapped[str | None] = mapped_column(Text)
    commit: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    used: Mapped[list[str] | None] = mapped_column(JSONType)
    generated: Mapped[list[str] | None] = mapped_column(JSONType)


class Snapshot(LiveBase):
    """An immutable, content-addressed frozen view.  Never updated."""

    __tablename__ = "snapshots"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    frozen_by: Mapped[str | None] = mapped_column(String(200))
    spec: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    schema_version: Mapped[str] = mapped_column(String(16), default="1.0")
    content: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    sha256: Mapped[str | None] = mapped_column(String(64))
    run_ids: Mapped[list[str] | None] = mapped_column(JSONType)
    all_runs_committed: Mapped[bool] = mapped_column(Boolean, default=False)
    eval_lab_commit: Mapped[str | None] = mapped_column(String(64))


class IngestLog(LiveBase):
    __tablename__ = "ingest_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    runner_id: Mapped[str | None] = mapped_column(String(200))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    payload_sha256: Mapped[str | None] = mapped_column(String(64))
    run_id: Mapped[str | None] = mapped_column(String(200))
    outcome: Mapped[str | None] = mapped_column(String(32))
    error: Mapped[str | None] = mapped_column(Text)


# --------------------------------------------------------------------- private


class Prediction(PrivateBase):
    """Per-record judge output.  For recompute and audits only.

    Deliberately has **no** record text, no prompt and no gold column: those
    never enter the database at all.  The public API role has no grant on this
    table, which is the second half of the leakage backstop.
    """

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(200), index=True)
    record_id: Mapped[str] = mapped_column(String(128), index=True)
    label: Mapped[str | None] = mapped_column(String(64))
    execution_status: Mapped[str | None] = mapped_column(String(32))
    latency_ms: Mapped[float | None] = mapped_column(Float)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float)
    provider_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONType)


class RunnerToken(PrivateBase):
    """Argon2-hashed ingest tokens (phase 3).  Never served."""

    __tablename__ = "runner_tokens"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    runner_id: Mapped[str] = mapped_column(String(200))
    token_hash: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(String(32), default="ingest")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


__all__ = [
    "SCHEMA_LIVE",
    "SCHEMA_PRIVATE",
    "Activity",
    "Aggregate",
    "Arm",
    "Artifact",
    "Comparison",
    "Dataset",
    "Dimension",
    "Experiment",
    "IngestLog",
    "Judge",
    "Level",
    "LiveBase",
    "Metric",
    "Observation",
    "Prediction",
    "PrivateBase",
    "Project",
    "Run",
    "RunEntity",
    "RunnerToken",
    "Snapshot",
    "utcnow",
]
