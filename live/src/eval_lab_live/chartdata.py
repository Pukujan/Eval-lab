"""Assemble ``research-chart-data`` v1 documents from database rows.

Every document this module returns validates against
``schemas/research-chart-data.v1.schema.json`` and is the *same document* the
papers embed: ``GET /api/v1/datasets/{id}`` rebuilds, from normalized tables,
exactly the bytes of ``paper/data/judges-blind-760.json`` (provenance included,
because the provenance block describes the frozen export the rows came from, and
the loader stores it verbatim).  ``live/tests/test_api_matches_paper.py`` is the
proof.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from sqlalchemy.orm import Session

from eval_lab_live import repository as repo
from eval_lab_live.models import (
    Aggregate,
    Arm,
    Comparison,
    Dataset,
    Dimension,
    Experiment,
    Level,
    Metric,
    Observation,
)

SCHEMA_VERSION = "1.0"
DOCUMENT_TYPE = ["schema:Dataset", "prov:Entity"]


def _arm_experiment_ids(arm: Arm) -> list[str]:
    """Every experiment an entity belongs to, primary first.

    These are the *short* ids (``EXP-013``) the document's ``experimentIds``
    array carries -- not the long ``arms.experiment_id`` foreign key.  The
    fallback covers a row written before ``experiment_ids`` existed.
    """
    ids = [str(item) for item in (arm.experiment_ids or [])]
    if not ids and arm.experiment:
        ids = [str(arm.experiment)]
    return ids


def entity_document(arm: Arm) -> dict[str, Any]:
    """One chart-data v1 ``entity``."""
    return {
        "id": arm.id,
        "label": arm.label,
        "shortLabel": arm.short_label,
        "headline": bool(arm.headline),
        "experiment": arm.experiment,
        "experimentIds": list(arm.experiment_ids or []),
        "deployment": arm.deployment,
        "modelFamily": arm.model_family,
        "modelId": arm.model_id,
        "paramsB": arm.params_b,
        "route": arm.route,
        "harness": arm.harness,
        "settings": dict(arm.config or {}),
        "settingsEvidence": list(arm.settings_evidence or []),
        "derived": bool(arm.derived),
        "rankAllRecord": arm.rank_all_record,
        "sharedRankAllRecord": arm.shared_rank_all_record,
        "recordCount": arm.record_count,
        "resolved": arm.resolved,
        "correct": arm.correct,
        "statusCounts": dict(arm.status_counts or {}),
    }


def observation_document(observation: Observation) -> dict[str, Any]:
    """One chart-data v1 ``observation``.

    ``slice_records`` is intentionally absent: it is an internal column used for
    the min-slice rule, not part of the schema (which forbids extra properties).
    """
    return {
        "entity": observation.entity_id,
        "slice": observation.slice_dim,
        "sliceValue": observation.slice_value,
        "metric": observation.metric_key,
        "value": observation.value,
        "ciLow": observation.ci_low,
        "ciHigh": observation.ci_high,
        "n": observation.n,
    }


def comparison_document(comparison: Comparison) -> dict[str, Any]:
    return {
        "left": comparison.left,
        "right": comparison.right,
        "view": comparison.view,
        "n": comparison.n,
        "leftOnlyCorrect": comparison.left_only_correct,
        "rightOnlyCorrect": comparison.right_only_correct,
        "pExact": comparison.p,
        "pHolm": comparison.p_holm,
    }


def aggregate_document(aggregate: Aggregate) -> dict[str, Any]:
    return {
        "key": aggregate.id,
        "metric": aggregate.metric_key,
        "method": aggregate.method,
        "over": aggregate.over,
        "value": aggregate.value,
        "ciLow": aggregate.ci_low,
        "ciHigh": aggregate.ci_high,
        "n": aggregate.n,
    }


def measure_document(metric: Metric) -> dict[str, Any]:
    return {
        "key": metric.key,
        "label": metric.label,
        "unit": metric.unit,
        "format": metric.format,
        "better": metric.better,
        "interval": metric.interval_method,
        "definition": metric.definition,
        "n": metric.n_label,
    }


def dimension_document(dimension: Dimension) -> dict[str, Any]:
    document: dict[str, Any] = {
        "key": dimension.key,
        "label": dimension.label,
        "type": dimension.type,
        "scope": dimension.scope,
    }
    if dimension.field is not None:
        document["field"] = dimension.field
    if dimension.unit is not None:
        document["unit"] = dimension.unit
    if dimension.values is not None:
        document["values"] = list(dimension.values)
    return document


def level_document(level: Level) -> dict[str, Any]:
    return {"key": level.key, "label": level.label, "description": level.description}


def experiment_document(experiment: Experiment, entity_ids: list[str]) -> dict[str, Any]:
    return {
        "id": experiment.short_id,
        "experimentId": experiment.id,
        "directory": experiment.directory,
        "status": experiment.status,
        "createdAt": experiment.created_at,
        "codeCommit": experiment.code_commit,
        "entities": entity_ids,
    }


def split_artifact_path(path: str) -> tuple[str, str, str]:
    """``(experimentShortId, experimentDirectory, runPath)`` for an artifact path.

    Mirrors ``scripts/export_chart_data.py`` exactly, including the ``"."``
    runPath used when an artifact sits directly in the experiment directory
    (``.../predictions-jev_pinned.jsonl``).
    """
    parts = PurePosixPath(path).parts
    experiment_short = f"EXP-{parts[1].split('-')[2]}" if len(parts) > 1 else ""
    experiment_directory = PurePosixPath(*parts[:2]).as_posix() if len(parts) > 1 else ""
    run_path = PurePosixPath(*parts[2:-1]).as_posix() or "." if len(parts) > 2 else "."
    return experiment_short, experiment_directory, run_path


def run_document(link: repo.RunLink) -> dict[str, Any]:
    experiment_short, experiment_directory, run_path = split_artifact_path(link.artifact_path)
    return {
        "entity": link.entity_id,
        "experiment": experiment_short,
        "experimentDirectory": experiment_directory,
        "runPath": run_path,
        "path": link.artifact_path,
        "sha256": link.artifact_sha256,
        "mergeOrder": link.merge_order,
    }


def build_document(
    session: Session,
    dataset: Dataset,
    *,
    filters: repo.DocumentFilters,
    min_slice_records: int,
    max_entities: int,
    max_observations: int,
    max_runs: int = 5000,
) -> dict[str, Any]:
    """Build one chart-data v1 dataset document.

    Raises :class:`repo.NotFound` when the filters select nothing and
    :class:`repo.InvalidQuery` when a query would exceed a cost cap.
    """
    level = filters.level
    arms = repo.list_arms(session, dataset.id, filters, limit=max_entities)
    if not arms:
        raise repo.NotFound("no entities match the requested filters")
    entity_ids = [arm.id for arm in arms]

    observations = repo.list_observations(
        session,
        dataset.id,
        entity_ids,
        filters,
        min_slice_records=min_slice_records,
        level=level,
        limit=max_observations,
    )
    if not observations:
        raise repo.NotFound("no observations match the requested filters")

    comparisons = repo.list_comparisons(session, dataset.id, entity_ids)
    aggregates = repo.list_aggregates(session, dataset.id)

    # The ``table`` level is "all observations; one row per arm/slice/metric",
    # so it drops the per-run provenance array and is the cheapest view.  Every
    # other level keeps it: ``runs`` is *about* those entries, and ``experiments``
    # is the same document grouped by experiment.
    include_runs = level in (None, "runs", "experiments")
    run_links: list[repo.RunLink] = []
    if include_runs:
        run_links = repo.list_runs_for_entities(session, dataset.id, entity_ids, limit=max_runs)

    # A merged entity belongs to more than one experiment (``qwen_flash_exp015_
    # 016`` was run in EXP-015 and EXP-016), and the document lists it under
    # both, so membership comes from ``experiment_ids`` and not from the arm's
    # single primary ``experiment_id``.  The export script emits the block in
    # ``sorted(short_id)`` order and leaves out an experiment with no member
    # entity, so both of those come from here rather than from the arm order.
    membership = [(arm.id, _arm_experiment_ids(arm)) for arm in arms]
    member_short_ids = sorted({short_id for _, ids in membership for short_id in ids})
    experiments_by_short_id = {
        experiment.short_id: experiment
        for experiment in repo.list_experiments_by_short_ids(session, member_short_ids)
    }
    member_short_ids = [
        short_id for short_id in member_short_ids if short_id in experiments_by_short_id
    ]

    document: dict[str, Any] = {
        "@context": dict(dataset.context or {}),
        "id": dataset.canonical_id,
        "type": list(DOCUMENT_TYPE),
        "kind": "dataset",
        "schemaVersion": dataset.version or SCHEMA_VERSION,
        "datasetId": dataset.id,
        "title": dataset.title,
        "description": dataset.description,
        "experimentId": dataset.experiment_id,
        "recordCount": dataset.record_count,
        "population": dict(dataset.population or {}),
        "provenance": dict(dataset.provenance or {}),
        "levels": [level_document(item) for item in repo.list_levels(session, dataset.id)],
        "dimensions": [
            dimension_document(item) for item in repo.list_dimensions(session, dataset.id)
        ],
        "measures": [measure_document(item) for item in repo.list_metrics(session, dataset.id)],
        "entities": [entity_document(arm) for arm in arms],
        "observations": [observation_document(item) for item in observations],
        "aggregates": [aggregate_document(item) for item in aggregates],
        "comparisons": [comparison_document(item) for item in comparisons],
        "experiments": [
            experiment_document(
                experiments_by_short_id[short_id],
                [arm_id for arm_id, ids in membership if short_id in ids],
            )
            for short_id in member_short_ids
        ],
        "runs": [run_document(link) for link in run_links],
        "notes": dict(dataset.notes or {}),
    }
    return document
