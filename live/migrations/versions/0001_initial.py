"""Initial live read-model schema.

Creates both schemas and every table the phase-2 backend needs.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LIVE = "live"
PRIVATE = "private"

#: ``JSONB`` on Postgres, plain ``JSON`` elsewhere -- mirrors
#: ``eval_lab_live.models.JSONType``.
JSON = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{LIVE}"')
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{PRIVATE}"')

    # ---------------------------------------------------------------- live
    op.create_table(
        "projects",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", TS, nullable=False),
        schema=LIVE,
    )

    op.create_table(
        "datasets",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("project_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("records_fingerprint", sa.String(64)),
        sa.Column("blind_ids_fingerprint", sa.String(64)),
        sa.Column("spec_fingerprint", sa.String(64)),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("public_count", sa.Integer(), nullable=False),
        sa.Column("blind_count", sa.Integer(), nullable=False),
        # NULL = use EVALLAB_LIVE_MIN_SLICE_RECORDS; 0 = serve the dataset in full.
        sa.Column("min_slice_records", sa.Integer()),
        sa.Column("split_policy", sa.Text()),
        sa.Column("canonical_id", sa.Text()),
        sa.Column("title", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("experiment_id", sa.String(64)),
        sa.Column("population", JSON),
        sa.Column("notes", JSON),
        sa.Column("provenance", JSON),
        sa.Column("context", JSON),
        sa.Column("created_at", TS, nullable=False),
        sa.ForeignKeyConstraint(["project_id"], [f"{LIVE}.projects.id"], ondelete="CASCADE"),
        schema=LIVE,
    )

    op.create_table(
        "experiments",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("project_id", sa.String(64), nullable=False),
        sa.Column("short_id", sa.String(16), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("hypothesis", sa.Text()),
        sa.Column("status", sa.String(64)),
        sa.Column("code_commit", sa.String(64)),
        sa.Column("created_at", sa.String(64)),
        sa.Column("directory", sa.Text(), nullable=False),
        sa.Column("manifest", JSON),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], [f"{LIVE}.projects.id"], ondelete="CASCADE"),
        schema=LIVE,
    )
    op.create_index("ix_experiments_short_id", "experiments", ["short_id"], schema=LIVE)

    op.create_table(
        "judges",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("project_id", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(64)),
        sa.Column("model", sa.String(200)),
        sa.Column("route", sa.Text()),
        sa.Column("family", sa.String(64)),
        sa.Column("params_b", sa.Float()),
        sa.Column("deployment", sa.String(32), nullable=False),
        sa.Column("short_label", sa.String(64)),
        sa.ForeignKeyConstraint(["project_id"], [f"{LIVE}.projects.id"], ondelete="CASCADE"),
        schema=LIVE,
    )

    op.create_table(
        "metrics",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.String(64), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("format", sa.String(32), nullable=False),
        sa.Column("better", sa.String(16), nullable=False),
        sa.Column("interval_method", sa.String(32), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("n_label", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], [f"{LIVE}.projects.id"], ondelete="CASCADE"),
        schema=LIVE,
    )

    op.create_table(
        "arms",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("dataset_id", sa.String(128), nullable=False),
        sa.Column("experiment_id", sa.String(128), nullable=False),
        sa.Column("judge_id", sa.String(128), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("short_label", sa.String(64), nullable=False),
        sa.Column("headline", sa.Boolean(), nullable=False),
        sa.Column("experiment", sa.String(64), nullable=False),
        sa.Column("experiment_ids", JSON, nullable=False),
        sa.Column("deployment", sa.String(32), nullable=False),
        sa.Column("model_family", sa.String(64)),
        sa.Column("model_id", sa.String(200)),
        sa.Column("params_b", sa.Float()),
        sa.Column("route", sa.Text()),
        sa.Column("harness", sa.Text()),
        sa.Column("config", JSON),
        sa.Column("config_hash", sa.String(64)),
        sa.Column("settings_evidence", JSON),
        sa.Column("derived", sa.Boolean(), nullable=False),
        sa.Column("rank_all_record", sa.Integer()),
        sa.Column("shared_rank_all_record", sa.Integer()),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("resolved", sa.Integer(), nullable=False),
        sa.Column("correct", sa.Integer(), nullable=False),
        sa.Column("status_counts", JSON),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], [f"{LIVE}.datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["experiment_id"], [f"{LIVE}.experiments.id"]),
        sa.ForeignKeyConstraint(["judge_id"], [f"{LIVE}.judges.id"]),
        schema=LIVE,
    )

    op.create_table(
        "levels",
        sa.Column("key", sa.String(32), primary_key=True),
        sa.Column("dataset_id", sa.String(128), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], [f"{LIVE}.datasets.id"], ondelete="CASCADE"),
        schema=LIVE,
    )

    op.create_table(
        "dimensions",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("dataset_id", sa.String(128), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("field", sa.String(64)),
        sa.Column("unit", sa.String(32)),
        sa.Column("values", JSON),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], [f"{LIVE}.datasets.id"], ondelete="CASCADE"),
        schema=LIVE,
    )

    op.create_table(
        "runs",
        sa.Column("run_id", sa.String(300), primary_key=True),
        sa.Column("source_run_id", sa.String(300)),
        sa.Column("dataset_id", sa.String(128), nullable=False),
        sa.Column("experiment_id", sa.String(128), nullable=False),
        sa.Column("arm_id", sa.String(128)),
        sa.Column("partition", sa.String(64)),
        sa.Column("status", sa.String(64)),
        sa.Column("started_at", TS),
        sa.Column("finished_at", TS),
        sa.Column("elapsed_s", sa.Float()),
        sa.Column("record_count", sa.Integer()),
        sa.Column("resolved_count", sa.Integer()),
        sa.Column("arm_summary", JSON),
        sa.Column("status_counts", JSON),
        sa.Column("code_commit", sa.String(64)),
        sa.Column("tree_dirty", sa.Boolean()),
        sa.Column("runner_host", sa.String(200)),
        sa.Column("git_committed", sa.Boolean(), nullable=False),
        sa.Column("eval_lab_commit", sa.String(64)),
        sa.Column("visibility", sa.String(32), nullable=False),
        sa.Column("ingest_id", sa.String(64)),
        sa.Column("results_path", sa.Text()),
        sa.Column("results_sha256", sa.String(64)),
        sa.Column("provider", sa.String(64)),
        sa.Column("requested_model", sa.String(200)),
        sa.Column("partition_fingerprints", JSON),
        sa.Column("execution", JSON),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], [f"{LIVE}.datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["experiment_id"], [f"{LIVE}.experiments.id"]),
        sa.ForeignKeyConstraint(["arm_id"], [f"{LIVE}.arms.id"]),
        schema=LIVE,
    )
    op.create_index("ix_runs_partition", "runs", ["partition"], schema=LIVE)

    op.create_table(
        "run_entities",
        sa.Column("run_id", sa.String(300), primary_key=True),
        sa.Column("entity_id", sa.String(128), primary_key=True),
        sa.Column("merge_order", sa.Integer(), nullable=False),
        sa.Column("artifact_path", sa.Text(), primary_key=True),
        sa.Column("artifact_sha256", sa.String(64)),
        sa.ForeignKeyConstraint(["run_id"], [f"{LIVE}.runs.run_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_id"], [f"{LIVE}.arms.id"], ondelete="CASCADE"),
        schema=LIVE,
    )

    op.create_table(
        "artifacts",
        sa.Column("run_id", sa.String(300), primary_key=True),
        sa.Column("path", sa.Text(), primary_key=True),
        sa.Column("sha256", sa.String(64)),
        sa.Column("bytes", sa.Integer()),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], [f"{LIVE}.runs.run_id"], ondelete="CASCADE"),
        schema=LIVE,
    )

    op.create_table(
        "observations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dataset_id", sa.String(128), nullable=False),
        sa.Column("entity_id", sa.String(128), nullable=False),
        sa.Column("metric_key", sa.String(64), nullable=False),
        sa.Column("slice_dim", sa.String(32), nullable=False),
        sa.Column("slice_value", sa.String(200), nullable=False),
        sa.Column("value", sa.Float()),
        sa.Column("ci_low", sa.Float()),
        sa.Column("ci_high", sa.Float()),
        sa.Column("n", sa.Integer(), nullable=False),
        # Internal only: the slice population the min-slice rule reads.  Never
        # serialized -- the chart-data observation schema forbids extra keys.
        sa.Column("slice_records", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], [f"{LIVE}.datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_id"], [f"{LIVE}.arms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["metric_key"], [f"{LIVE}.metrics.key"]),
        schema=LIVE,
    )
    op.create_index("ix_observations_entity_id", "observations", ["entity_id"], schema=LIVE)
    op.create_index("ix_observations_metric_key", "observations", ["metric_key"], schema=LIVE)
    op.create_index("ix_observations_slice_dim", "observations", ["slice_dim"], schema=LIVE)

    op.create_table(
        "aggregates",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("dataset_id", sa.String(128), nullable=False),
        sa.Column("metric_key", sa.String(64), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("over", sa.String(64), nullable=False),
        sa.Column("derived_from_run_ids", JSON, nullable=False),
        sa.Column("value", sa.Float()),
        sa.Column("ci_low", sa.Float()),
        sa.Column("ci_high", sa.Float()),
        sa.Column("n", sa.Integer()),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], [f"{LIVE}.datasets.id"], ondelete="CASCADE"),
        schema=LIVE,
    )

    op.create_table(
        "comparisons",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dataset_id", sa.String(128), nullable=False),
        sa.Column("left", sa.String(128), nullable=False),
        sa.Column("right", sa.String(128), nullable=False),
        sa.Column("view", sa.String(16), nullable=False),
        sa.Column("test", sa.String(64), nullable=False),
        sa.Column("statistic", sa.Float()),
        sa.Column("p", sa.Float()),
        sa.Column("p_holm", sa.Float()),
        sa.Column("n", sa.Integer(), nullable=False),
        sa.Column("left_only_correct", sa.Integer(), nullable=False),
        sa.Column("right_only_correct", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(64)),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], [f"{LIVE}.datasets.id"], ondelete="CASCADE"),
        schema=LIVE,
    )

    op.create_table(
        "activities",
        sa.Column("id", sa.String(200), primary_key=True),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("agent", sa.String(200)),
        sa.Column("software", sa.Text()),
        sa.Column("commit", sa.String(64)),
        sa.Column("started_at", TS),
        sa.Column("ended_at", TS),
        sa.Column("used", JSON),
        sa.Column("generated", JSON),
        schema=LIVE,
    )

    op.create_table(
        "snapshots",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("created_at", TS, nullable=False),
        sa.Column("frozen_by", sa.String(200)),
        sa.Column("spec", JSON),
        sa.Column("schema_version", sa.String(16), nullable=False),
        sa.Column("content", JSON),
        sa.Column("sha256", sa.String(64)),
        sa.Column("run_ids", JSON),
        sa.Column("all_runs_committed", sa.Boolean(), nullable=False),
        sa.Column("eval_lab_commit", sa.String(64)),
        schema=LIVE,
    )

    op.create_table(
        "ingest_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("runner_id", sa.String(200)),
        sa.Column("received_at", TS, nullable=False),
        sa.Column("payload_sha256", sa.String(64)),
        sa.Column("run_id", sa.String(200)),
        sa.Column("outcome", sa.String(32)),
        sa.Column("error", sa.Text()),
        schema=LIVE,
    )

    # ------------------------------------------------------------- private
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(200), nullable=False),
        sa.Column("record_id", sa.String(128), nullable=False),
        sa.Column("label", sa.String(64)),
        sa.Column("execution_status", sa.String(32)),
        sa.Column("latency_ms", sa.Float()),
        sa.Column("prompt_tokens", sa.Integer()),
        sa.Column("completion_tokens", sa.Integer()),
        sa.Column("cost_usd", sa.Float()),
        sa.Column("provider_metadata", JSON),
        schema=PRIVATE,
    )
    op.create_index("ix_predictions_run_id", "predictions", ["run_id"], schema=PRIVATE)
    op.create_index("ix_predictions_record_id", "predictions", ["record_id"], schema=PRIVATE)

    op.create_table(
        "runner_tokens",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("runner_id", sa.String(200), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("scope", sa.String(32), nullable=False),
        sa.Column("created_at", TS, nullable=False),
        sa.Column("revoked_at", TS),
        sa.Column("last_used_at", TS),
        schema=PRIVATE,
    )


def downgrade() -> None:
    op.drop_table("runner_tokens", schema=PRIVATE)
    op.drop_index("ix_predictions_record_id", table_name="predictions", schema=PRIVATE)
    op.drop_index("ix_predictions_run_id", table_name="predictions", schema=PRIVATE)
    op.drop_table("predictions", schema=PRIVATE)

    op.drop_table("ingest_log", schema=LIVE)
    op.drop_table("snapshots", schema=LIVE)
    op.drop_table("activities", schema=LIVE)
    op.drop_table("comparisons", schema=LIVE)
    op.drop_table("aggregates", schema=LIVE)
    for index in (
        "ix_observations_slice_dim",
        "ix_observations_metric_key",
        "ix_observations_entity_id",
    ):
        op.drop_index(index, table_name="observations", schema=LIVE)
    op.drop_table("observations", schema=LIVE)
    op.drop_table("artifacts", schema=LIVE)
    op.drop_table("run_entities", schema=LIVE)
    op.drop_index("ix_runs_partition", table_name="runs", schema=LIVE)
    op.drop_table("runs", schema=LIVE)
    op.drop_table("dimensions", schema=LIVE)
    op.drop_table("levels", schema=LIVE)
    op.drop_table("arms", schema=LIVE)
    op.drop_table("metrics", schema=LIVE)
    op.drop_table("judges", schema=LIVE)
    op.drop_index("ix_experiments_short_id", table_name="experiments", schema=LIVE)
    op.drop_table("experiments", schema=LIVE)
    op.drop_table("datasets", schema=LIVE)
    op.drop_table("projects", schema=LIVE)
