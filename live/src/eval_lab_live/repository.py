"""Read-only queries that feed the chart-data document builder.

Nothing here writes, and nothing here touches the ``private`` schema: the public
API's database role could not read it even if it tried (see
``live/tests/test_roles_pg.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from eval_lab_live.models import (
    Aggregate,
    Arm,
    Artifact,
    Comparison,
    Dataset,
    Dimension,
    Experiment,
    Judge,
    Level,
    Metric,
    Observation,
    Project,
    Run,
    RunEntity,
    Snapshot,
)

#: Levels exposed by the explorer, mirroring ``export_chart_data.LEVELS``.
LEVELS = ("summary", "breakdown", "experiments", "runs", "table")


class NotFound(LookupError):
    """Raised when a requested row does not exist."""


class InvalidQuery(ValueError):
    """Raised for a query the public API refuses to answer."""


@dataclass(frozen=True)
class DocumentFilters:
    """Filters accepted by the document endpoints.

    Deliberately closed-ended: every value is matched against a column, never
    interpolated, and the result set is capped by the caller.
    """

    entities: tuple[str, ...] = ()
    experiments: tuple[str, ...] = ()
    deployments: tuple[str, ...] = ()
    model_families: tuple[str, ...] = ()
    metrics: tuple[str, ...] = ()
    slices: tuple[str, ...] = ()
    slice_values: tuple[str, ...] = ()
    headline_only: bool = False
    level: str | None = None

    def is_empty(self) -> bool:
        return not any(
            (
                self.entities,
                self.experiments,
                self.deployments,
                self.model_families,
                self.metrics,
                self.slices,
                self.slice_values,
                self.headline_only,
            )
        )


def get_project(session: Session, project_id: str) -> Project:
    project: Project | None = session.get(Project, project_id)
    if project is None:
        raise NotFound(f"unknown project: {project_id}")
    return project


def list_projects(session: Session) -> list[Project]:
    return list(session.scalars(select(Project).order_by(Project.id)))


def list_datasets(session: Session, project_id: str | None = None) -> list[Dataset]:
    stmt = select(Dataset).order_by(Dataset.id)
    if project_id is not None:
        stmt = stmt.where(Dataset.project_id == project_id)
    return list(session.scalars(stmt))


def get_dataset(session: Session, dataset_id: str) -> Dataset:
    dataset: Dataset | None = session.get(Dataset, dataset_id)
    if dataset is None:
        raise NotFound(f"unknown dataset: {dataset_id}")
    return dataset


def list_experiments(session: Session, dataset_id: str | None = None) -> list[Experiment]:
    stmt = select(Experiment).order_by(Experiment.position, Experiment.id)
    if dataset_id is not None:
        stmt = stmt.where(
            Experiment.id.in_(select(Arm.experiment_id).where(Arm.dataset_id == dataset_id))
        )
    return list(session.scalars(stmt))


def list_judges(session: Session, dataset_id: str | None = None) -> list[Judge]:
    stmt = select(Judge).order_by(Judge.id)
    if dataset_id is not None:
        stmt = stmt.where(Judge.id.in_(select(Arm.judge_id).where(Arm.dataset_id == dataset_id)))
    return list(session.scalars(stmt))


def list_metrics(session: Session, dataset_id: str | None = None) -> list[Metric]:
    stmt = select(Metric).order_by(Metric.position, Metric.key)
    if dataset_id is not None:
        stmt = stmt.where(
            Metric.key.in_(
                select(Observation.metric_key).where(Observation.dataset_id == dataset_id)
            )
        )
    return list(session.scalars(stmt))


def list_levels(session: Session, dataset_id: str) -> list[Level]:
    return list(
        session.scalars(
            select(Level).where(Level.dataset_id == dataset_id).order_by(Level.position)
        )
    )


def list_dimensions(session: Session, dataset_id: str) -> list[Dimension]:
    return list(
        session.scalars(
            select(Dimension).where(Dimension.dataset_id == dataset_id).order_by(Dimension.position)
        )
    )


def _arm_query(dataset_id: str, filters: DocumentFilters) -> Select[tuple[Arm]]:
    stmt = select(Arm).where(Arm.dataset_id == dataset_id)
    if filters.entities:
        stmt = stmt.where(Arm.id.in_(filters.entities))
    if filters.experiments:
        stmt = stmt.where(Arm.experiment.in_(filters.experiments))
    if filters.deployments:
        stmt = stmt.where(Arm.deployment.in_(filters.deployments))
    if filters.model_families:
        stmt = stmt.where(Arm.model_family.in_(filters.model_families))
    if filters.headline_only:
        stmt = stmt.where(Arm.headline.is_(True))
    return stmt.order_by(Arm.position, Arm.id)


def list_arms(
    session: Session, dataset_id: str, filters: DocumentFilters, *, limit: int
) -> list[Arm]:
    arms = list(session.scalars(_arm_query(dataset_id, filters)))
    if len(arms) > limit:
        raise InvalidQuery(
            f"query selects {len(arms)} entities, which exceeds the {limit}-entity cap; "
            "narrow it with filters"
        )
    return arms


def list_observations(
    session: Session,
    dataset_id: str,
    entity_ids: list[str],
    filters: DocumentFilters,
    *,
    min_slice_records: int,
    level: str | None,
    limit: int,
) -> list[Observation]:
    if not entity_ids:
        return []
    stmt = select(Observation).where(
        Observation.dataset_id == dataset_id, Observation.entity_id.in_(entity_ids)
    )
    if filters.metrics:
        stmt = stmt.where(Observation.metric_key.in_(filters.metrics))
    if filters.slices:
        stmt = stmt.where(Observation.slice_dim.in_(filters.slices))
    if filters.slice_values:
        stmt = stmt.where(Observation.slice_value.in_(filters.slice_values))
    if level == "summary":
        stmt = stmt.where(Observation.slice_dim == "overall")
    elif level == "breakdown":
        stmt = stmt.where(Observation.slice_dim != "overall")
    elif level in {"experiments", "runs"}:
        stmt = stmt.where(Observation.slice_dim == "overall")
    if min_slice_records > 0:
        stmt = stmt.where(
            (Observation.slice_records >= min_slice_records) | (Observation.slice_dim == "overall")
        )
    observations = list(session.scalars(stmt.order_by(Observation.position, Observation.id)))
    if len(observations) > limit:
        raise InvalidQuery(
            f"query selects {len(observations)} observations, which exceeds the "
            f"{limit}-observation cap; narrow it with filters"
        )
    return observations


def list_comparisons(session: Session, dataset_id: str, entity_ids: list[str]) -> list[Comparison]:
    if not entity_ids:
        return []
    return list(
        session.scalars(
            select(Comparison)
            .where(
                Comparison.dataset_id == dataset_id,
                Comparison.left.in_(entity_ids),
                Comparison.right.in_(entity_ids),
            )
            .order_by(Comparison.position, Comparison.id)
        )
    )


def list_aggregates(session: Session, dataset_id: str) -> list[Aggregate]:
    return list(
        session.scalars(
            select(Aggregate)
            .where(Aggregate.dataset_id == dataset_id)
            .order_by(Aggregate.position, Aggregate.id)
        )
    )


class RunLink(NamedTuple):
    """One ``runs[]`` entry of a chart-data document."""

    run: Run
    entity_id: str
    merge_order: int
    artifact_path: str
    artifact_sha256: str | None


def list_runs_for_entities(
    session: Session, dataset_id: str, entity_ids: list[str], *, limit: int
) -> list[RunLink]:
    """The runs feeding the given entities, in chart-data document order.

    Order is entity order (the same order the entities appear in), then the
    declared merge order inside an entity.
    """
    if not entity_ids:
        return []
    rows = session.execute(
        select(Run, RunEntity, Arm.position)
        .join(RunEntity, RunEntity.run_id == Run.run_id)
        .join(Arm, Arm.id == RunEntity.entity_id)
        .where(Run.dataset_id == dataset_id, RunEntity.entity_id.in_(entity_ids))
        .order_by(Arm.position, Arm.id, RunEntity.merge_order)
    ).all()
    if len(rows) > limit:
        raise InvalidQuery(f"query selects {len(rows)} runs, which exceeds the {limit}-run cap")
    return [
        RunLink(
            run=row[0],
            entity_id=row[1].entity_id,
            merge_order=row[1].merge_order,
            artifact_path=row[1].artifact_path,
            artifact_sha256=row[1].artifact_sha256,
        )
        for row in rows
    ]


def list_experiments_by_ids(session: Session, ids: list[str]) -> list[Experiment]:
    if not ids:
        return []
    return list(
        session.scalars(
            select(Experiment)
            .where(Experiment.id.in_(ids))
            .order_by(Experiment.position, Experiment.id)
        )
    )


def get_run(session: Session, run_id: str) -> Run:
    run: Run | None = session.get(Run, run_id)
    if run is None:
        raise NotFound(f"unknown run: {run_id}")
    return run


def list_runs(session: Session, dataset_id: str | None = None) -> list[Run]:
    stmt = select(Run).order_by(Run.experiment_id, Run.run_id)
    if dataset_id is not None:
        stmt = stmt.where(Run.dataset_id == dataset_id)
    return list(session.scalars(stmt))


def list_artifacts(session: Session, run_id: str) -> list[Artifact]:
    return list(
        session.scalars(select(Artifact).where(Artifact.run_id == run_id).order_by(Artifact.path))
    )


def list_snapshots(session: Session) -> list[Snapshot]:
    return list(session.scalars(select(Snapshot).order_by(Snapshot.created_at.desc())))


def get_snapshot(session: Session, snapshot_id: str) -> Snapshot:
    snapshot: Snapshot | None = session.get(Snapshot, snapshot_id)
    if snapshot is None:
        raise NotFound(f"unknown snapshot: {snapshot_id}")
    return snapshot


@dataclass
class Facets:
    """Available filter values, so the explorer never offers a dead end."""

    entities: list[str] = field(default_factory=list)
    experiments: list[str] = field(default_factory=list)
    deployments: list[str] = field(default_factory=list)
    model_families: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    slices: list[str] = field(default_factory=list)
    slice_values: dict[str, list[str]] = field(default_factory=dict)
    levels: list[str] = field(default_factory=list)


def facets(session: Session, dataset_id: str) -> Facets:
    arms = list(session.scalars(select(Arm).where(Arm.dataset_id == dataset_id)))
    observations = list(
        session.scalars(select(Observation).where(Observation.dataset_id == dataset_id))
    )
    metrics = list_metrics(session, dataset_id)
    levels = list_levels(session, dataset_id)
    slice_values: dict[str, list[str]] = {}
    for observation in observations:
        bucket = slice_values.setdefault(observation.slice_dim, [])
        if observation.slice_value not in bucket:
            bucket.append(observation.slice_value)
    return Facets(
        entities=[arm.id for arm in arms],
        experiments=sorted({arm.experiment for arm in arms}),
        deployments=sorted({arm.deployment for arm in arms}),
        model_families=sorted({arm.model_family for arm in arms if arm.model_family}),
        metrics=[metric.key for metric in metrics],
        slices=sorted(slice_values),
        slice_values={key: sorted(values) for key, values in sorted(slice_values.items())},
        levels=[level.key for level in levels],
    )


__all__ = [
    "LEVELS",
    "DocumentFilters",
    "Facets",
    "InvalidQuery",
    "NotFound",
    "RunLink",
    "facets",
    "get_dataset",
    "get_project",
    "get_run",
    "get_snapshot",
    "list_aggregates",
    "list_arms",
    "list_artifacts",
    "list_comparisons",
    "list_datasets",
    "list_dimensions",
    "list_experiments",
    "list_experiments_by_ids",
    "list_judges",
    "list_levels",
    "list_metrics",
    "list_observations",
    "list_projects",
    "list_runs",
    "list_runs_for_entities",
    "list_snapshots",
]
