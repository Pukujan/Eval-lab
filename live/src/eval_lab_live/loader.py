"""Backfill the live database from the committed repository.

The loader is the phase-2 answer to "the database is a rebuildable projection of
git": it reads ``experiments/*`` (every committed run), and it recomputes the
paper's chart-data dataset through the **same code path the paper uses** --
``scripts/analyze_judge_comparison.py`` and ``scripts/export_chart_data.py`` --
so the live numbers cannot drift from the published ones.  Nothing here calls a
model or a provider, and nothing here reads a secret.

Two things are imported:

*Every run*
    Each ``experiments/EXP-*/**/results.json`` becomes a ``runs`` row with its
    partition, per-arm summary, source-pool fingerprints, artifact hashes
    (``checksums.sha256``) and a ``run_entities`` link to the chart entity it
    feeds.  Files without a ``run_id`` (older runners) are keyed by their
    repository path, so nothing is dropped.

*The frozen dataset*
    ``paper/data/judges-blind-760.json`` is recomputed by
    :func:`scripts.export_chart_data.build_dataset` and decomposed into
    ``arms``/``observations``/``comparisons``/``metrics``/``dimensions``/
    ``levels`` rows.  The freshly computed document is compared against the
    committed file before anything is written; a mismatch aborts the load
    instead of publishing numbers that disagree with the paper.  The committed
    file's ``provenance`` block is stored verbatim, because it is the record of
    where those numbers came from.

Usage::

    uv run --extra live python -m eval_lab_live.loader --reset
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from eval_lab_live.models import (
    Activity,
    Aggregate,
    Arm,
    Artifact,
    Comparison,
    Dataset,
    Dimension,
    Experiment,
    Judge,
    Level,
    LiveBase,
    Metric,
    Observation,
    PrivateBase,
    Project,
    Run,
    RunEntity,
)

DEFAULT_PROJECT = "eval-lab"
DEFAULT_DATASET = "eval-lab/judges-blind-760"
REPO_URL = "https://github.com/Pukujan/Eval-lab"
CHECKSUM_LINE = re.compile(r"^(?P<sha256>[0-9a-f]{64})\s+\*?(?P<path>.+)$")
DATASET_FILE = "paper/data/judges-blind-760.json"

#: Datasets served in full, with no min-slice suppression.
#:
#: The min-slice rule (architecture doc section 11) exists so filters cannot
#: narrow a *secret* blind partition down to individual items.  It does not
#: apply here: all 760 records and their gold labels are already in this public
#: repository, which is exactly what the architecture doc's Decision 2 records,
#: and the papers publish the small slices themselves ("Eval Lab synthetic"
#: holds 8 and 12 records).  Suppressing them would hide published numbers and
#: make the API disagree with ``paper/data/judges-blind-760.json``.
#:
#: Every other dataset keeps ``min_slice_records = NULL``, so the configured
#: threshold applies.  Phase 3's ingest sets it per dataset.
PUBLISHED_DATASETS = frozenset({DEFAULT_DATASET})


class LoadError(RuntimeError):
    """Raised when the repository and the database would disagree."""


@dataclass
class LoadReport:
    project: str = DEFAULT_PROJECT
    dataset: str = DEFAULT_DATASET
    experiments: int = 0
    judges: int = 0
    arms: int = 0
    metrics: int = 0
    dimensions: int = 0
    levels: int = 0
    observations: int = 0
    comparisons: int = 0
    aggregates: int = 0
    runs: int = 0
    runs_without_id: int = 0
    #: Runs whose ``results.json`` carried a ``run_id`` that another committed
    #: run already used.  They are imported all the same, keyed by their run
    #: directory, with the runner's value kept in ``runs.source_run_id``.
    duplicate_run_ids: int = 0
    run_entities: int = 0
    artifacts: int = 0
    activities: int = 0
    skipped: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"{self.experiments} experiments, {self.judges} judges, {self.arms} arms, "
            f"{self.observations} observations, {self.comparisons} comparisons, "
            f"{self.runs} runs ({self.runs_without_id} keyed by path, "
            f"{self.duplicate_run_ids} re-keyed on a duplicate run_id), "
            f"{self.run_entities} run links, {self.artifacts} artifacts"
        )


# --------------------------------------------------------------------- helpers
def _scripts(name: str, repo_root: Path) -> Any:
    """Import a repository script, tolerating an uninstalled checkout."""
    try:
        return importlib.import_module(f"scripts.{name}")
    except ImportError:
        root = str(repo_root)
        if root not in sys.path:
            sys.path.insert(0, root)
        return importlib.import_module(f"scripts.{name}")


def sha256_file(path: Path) -> str:
    """SHA-256 of the LF-normalized bytes, so CRLF checkouts hash identically."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonable(value: Any) -> Any:
    """Make YAML-derived values storable in a JSON column.

    ``experiment.yaml`` timestamps parse into ``datetime`` objects, which the
    JSON columns cannot hold; JSON input (``results.json``) is already plain.
    """
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse an ISO-8601 timestamp, tolerating a trailing ``Z`` (Python 3.11+ does)."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _rel(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _experiment_directories(repo_root: Path) -> list[Path]:
    root = repo_root / "experiments"
    if not root.is_dir():
        raise LoadError(f"no experiments directory under {repo_root}")
    return sorted(path for path in root.glob("EXP-*") if path.is_dir())


def _short_id(experiment_dir: Path) -> str:
    return f"EXP-{experiment_dir.name.split('-')[2]}"


def _experiment_dir_of(path: Path, repo_root: Path) -> Path | None:
    """The ``experiments/EXP-*`` directory that owns ``path``."""
    experiments_root = (repo_root / "experiments").resolve()
    for ancestor in path.resolve().parents:
        if ancestor.parent == experiments_root:
            return ancestor
    return None


def _iter_results_files(repo_root: Path) -> Iterator[Path]:
    for path in sorted((repo_root / "experiments").rglob("results.json")):
        if path.is_file():
            yield path.resolve()


def _resolve_run_dir(artifact: Path, repo_root: Path) -> Path | None:
    """The deepest ancestor directory that has its own ``results.json``."""
    experiment_dir = _experiment_dir_of(artifact, repo_root)
    current = artifact.resolve().parent
    for _ in range(6):
        if (current / "results.json").is_file():
            return current
        if experiment_dir is None or current == experiment_dir:
            break
        current = current.parent
    return experiment_dir


def _read_checksums(run_dir: Path, repo_root: Path) -> list[tuple[str, str, int | None]]:
    """``(repo-relative path, sha256, bytes)`` from a ``checksums.sha256`` file."""
    path = run_dir / "checksums.sha256"
    if not path.is_file():
        return []
    rows: list[tuple[str, str, int | None]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = CHECKSUM_LINE.match(line.strip())
        if not match:
            continue
        rel = match.group("path").strip().strip('"')
        target = run_dir / rel
        size = target.stat().st_size if target.is_file() else None
        rows.append((_rel(target, repo_root), match.group("sha256"), size))
    return rows


# -------------------------------------------------------------------- importers
def import_project(session: Session, project_id: str) -> Project:
    existing: Project | None = session.get(Project, project_id)
    if existing is not None:
        return existing
    project = Project(
        id=project_id,
        name="Eval Lab",
        description=(
            "Objective-grounded judge evaluation: accuracy, coverage and calibration "
            "of lightweight judges on typed decisions with objective gold labels."
        ),
    )
    session.add(project)
    session.flush()
    return project


def import_experiments(session: Session, repo_root: Path, project_id: str) -> dict[str, Experiment]:
    import yaml

    rows: dict[str, Experiment] = {}
    for position, directory in enumerate(_experiment_directories(repo_root)):
        manifest_path = directory / "experiment.yaml"
        manifest: dict[str, Any] = {}
        if manifest_path.is_file():
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        experiment_id = str(manifest.get("id") or directory.name)
        created = manifest.get("created_at")
        row = Experiment(
            id=experiment_id,
            project_id=project_id,
            short_id=_short_id(directory),
            title=manifest.get("title"),
            hypothesis=manifest.get("hypothesis"),
            status=manifest.get("status"),
            code_commit=manifest.get("code_commit"),
            created_at=str(created) if created is not None else None,
            directory=_rel(directory, repo_root),
            manifest=_jsonable(manifest),
            position=position,
        )
        session.merge(row)
        rows[directory.name] = row
    session.flush()
    return rows


def import_runs(
    session: Session,
    repo_root: Path,
    experiments: dict[str, Experiment],
    dataset_id: str,
    report: LoadReport,
) -> dict[Path, str]:
    """Import every committed ``results.json``.

    Returns a map from resolved run directory to ``run_id`` so the chart-data
    ``runs[]`` entries can be linked afterwards.
    """
    run_dirs: dict[Path, str] = {}
    seen_run_ids: dict[str, Path] = {}
    for results_path in _iter_results_files(repo_root):
        try:
            payload = _read_json(results_path)
        except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover - defensive
            report.skipped.append(f"{_rel(results_path, repo_root)}: unreadable ({exc})")
            continue
        if not isinstance(payload, dict):
            report.skipped.append(f"{_rel(results_path, repo_root)}: not a JSON object")
            continue
        experiment_dir = _experiment_dir_of(results_path, repo_root)
        if experiment_dir is None:
            report.skipped.append(f"{_rel(results_path, repo_root)}: not inside an EXP-* directory")
            continue
        experiment = experiments.get(experiment_dir.name)
        if experiment is None:  # pragma: no cover - defensive
            report.skipped.append(f"{_rel(results_path, repo_root)}: unknown experiment")
            continue
        run_dir = results_path.parent
        #: The value the runner wrote, when it is not the row key.
        source_run_id: str | None = None
        reported = payload.get("run_id")
        if isinstance(reported, str) and reported:
            run_id = reported
        else:
            # Older runners wrote a results.json with no run_id.  Key it by its
            # repository path: stable, unique, and traceable back to the file.
            run_id = _rel(run_dir, repo_root)
            report.runs_without_id += 1
        if run_id in seen_run_ids:
            # A runner id is unique inside its experiment, not across the
            # repository: two committed runs reuse one.  Re-key this one by its
            # run directory -- the same identity a file with no run_id gets --
            # and keep the runner's value, so no run is dropped and nothing the
            # runner wrote is lost.
            source_run_id = run_id
            run_id = _rel(run_dir, repo_root)
            report.duplicate_run_ids += 1
        seen_run_ids[run_id] = run_dir
        run_dirs[run_dir] = run_id
        session.merge(
            _run_row(
                payload,
                run_id,
                results_path,
                run_dir,
                experiment.id,
                dataset_id,
                repo_root,
                source_run_id=source_run_id,
            )
        )
        report.runs += 1

        for artifact_path, artifact_sha256, size in _read_checksums(run_dir, repo_root):
            session.merge(
                Artifact(
                    run_id=run_id,
                    path=artifact_path,
                    sha256=artifact_sha256,
                    bytes=size,
                    kind="checksum",
                )
            )
            report.artifacts += 1
        session.merge(
            Activity(
                id=f"urn:eval-lab:run:{run_id}",
                type="run",
                agent=payload.get("runner_host"),
                software=payload.get("provider"),
                commit=payload.get("code_commit"),
                started_at=_parse_timestamp(payload.get("created_at_utc")),
                ended_at=_parse_timestamp(payload.get("created_at_utc")),
                used=[_rel(results_path, repo_root)],
                generated=[run_id],
            )
        )
        report.activities += 1
    session.flush()
    return run_dirs


def _run_row(
    payload: dict[str, Any],
    run_id: str,
    results_path: Path,
    run_dir: Path,
    experiment_id: str,
    dataset_id: str,
    repo_root: Path,
    *,
    source_run_id: str | None = None,
) -> Run:
    arms_raw: Any = payload.get("arms")
    arms: dict[str, Any] = arms_raw if isinstance(arms_raw, dict) else {}
    arm_summary: dict[str, Any] = {}
    status_counts: dict[str, int] = {}
    for key, arm_payload in sorted(arms.items()):
        if not isinstance(arm_payload, dict):
            continue
        aggregate = (arm_payload.get("metrics") or {}).get("aggregate") or {}
        arm_summary[str(key)] = {
            "count": aggregate.get("count"),
            "correct": arm_payload.get("correct_count"),
            "accuracy": arm_payload.get("accuracy"),
        }
        error_kinds: dict[str, Any] = arm_payload.get("error_kinds") or {}
        for kind, value in error_kinds.items():
            if isinstance(value, int):
                status_counts[kind] = status_counts.get(kind, 0) + value
    resolved_counts = [
        entry["count"] for entry in arm_summary.values() if isinstance(entry.get("count"), int)
    ]
    source_pool = (
        payload.get("source_pool") if isinstance(payload.get("source_pool"), dict) else None
    )
    created = _parse_timestamp(payload.get("created_at_utc"))
    record_count = payload.get("record_count")
    return Run(
        run_id=run_id,
        source_run_id=source_run_id,
        dataset_id=dataset_id,
        experiment_id=experiment_id,
        partition=payload.get("partition") if isinstance(payload.get("partition"), str) else None,
        status=payload.get("status") if isinstance(payload.get("status"), str) else None,
        started_at=created,
        finished_at=created,
        record_count=record_count if isinstance(record_count, int) else None,
        resolved_count=max(resolved_counts) if resolved_counts else None,
        arm_summary=arm_summary or None,
        status_counts=dict(sorted(status_counts.items())) or None,
        code_commit=payload.get("code_commit"),
        tree_dirty=payload.get("tree_dirty")
        if isinstance(payload.get("tree_dirty"), bool)
        else None,
        runner_host=payload.get("runner_host"),
        git_committed=True,
        eval_lab_commit=payload.get("code_commit"),
        visibility="public",
        results_path=_rel(results_path, repo_root),
        results_sha256=sha256_file(results_path),
        provider=payload.get("provider"),
        requested_model=payload.get("requested_model"),
        partition_fingerprints=source_pool,
        execution=payload.get("execution") if isinstance(payload.get("execution"), dict) else None,
    )


def _decompose_dataset(
    session: Session,
    document: dict[str, Any],
    committed: dict[str, Any],
    project_id: str,
    dataset_id: str,
    report: LoadReport,
) -> None:
    """Write the chart-data document's parts into their own tables."""
    policy = (committed.get("provenance") or {}).get("policy") or {}
    session.merge(
        Dataset(
            id=dataset_id,
            project_id=project_id,
            name=document["title"],
            version=document["schemaVersion"],
            record_count=int(document.get("recordCount") or 0),
            blind_count=int((document.get("population") or {}).get("records") or 0),
            public_count=0,
            min_slice_records=0 if dataset_id in PUBLISHED_DATASETS else None,
            split_policy=policy.get("blind_holdout"),
            canonical_id=document.get("id"),
            title=document.get("title"),
            description=document.get("description"),
            experiment_id=document.get("experimentId"),
            population=document.get("population"),
            notes=document.get("notes"),
            provenance=committed.get("provenance"),
            context=document.get("@context"),
        )
    )
    session.flush()

    for position, measure in enumerate(document.get("measures") or []):
        session.merge(
            Metric(
                key=measure["key"],
                project_id=project_id,
                label=measure["label"],
                unit=measure["unit"],
                format=measure["format"],
                better=measure["better"],
                interval_method=measure["interval"],
                definition=measure["definition"],
                n_label=measure["n"],
                position=position,
            )
        )
        report.metrics += 1

    for position, level in enumerate(document.get("levels") or []):
        session.merge(
            Level(
                key=level["key"],
                dataset_id=dataset_id,
                label=level["label"],
                description=level["description"],
                position=position,
            )
        )
        report.levels += 1

    for position, dimension in enumerate(document.get("dimensions") or []):
        session.merge(
            Dimension(
                key=dimension["key"],
                dataset_id=dataset_id,
                label=dimension["label"],
                type=dimension["type"],
                scope=dimension["scope"],
                field=dimension.get("field"),
                unit=dimension.get("unit"),
                values=dimension.get("values"),
                position=position,
            )
        )
        report.dimensions += 1

    # Slice population: the ``n`` of the all-record-accuracy observation of the
    # same (entity, slice, sliceValue) cell is exactly the number of records in
    # that slice, which is what the min-slice rule measures.
    slice_records: dict[tuple[str, str, str], int] = {}
    for observation in document.get("observations") or []:
        if observation["metric"] == "all_record_accuracy":
            key = (observation["entity"], observation["slice"], observation["sliceValue"])
            slice_records[key] = int(observation["n"])

    judge_ids: set[str] = set()
    for position, entity in enumerate(document.get("entities") or []):
        experiment_id = _experiment_id_for(session, entity["experimentIds"][0])
        judge_id = _judge_id_for(entity)
        if judge_id not in judge_ids:
            session.merge(_judge_row(entity, judge_id, project_id))
            judge_ids.add(judge_id)
        session.merge(
            Arm(
                id=entity["id"],
                dataset_id=dataset_id,
                experiment_id=experiment_id,
                judge_id=judge_id,
                label=entity["label"],
                short_label=entity["shortLabel"],
                headline=bool(entity.get("headline")),
                experiment=entity["experiment"],
                experiment_ids=list(entity["experimentIds"]),
                deployment=entity["deployment"],
                model_family=entity.get("modelFamily"),
                model_id=entity.get("modelId"),
                params_b=entity.get("paramsB"),
                route=entity.get("route"),
                harness=entity.get("harness"),
                config=entity.get("settings"),
                config_hash=_config_hash(entity.get("settings")),
                settings_evidence=entity.get("settingsEvidence"),
                derived=bool(entity.get("derived")),
                rank_all_record=entity.get("rankAllRecord"),
                shared_rank_all_record=entity.get("sharedRankAllRecord"),
                record_count=int(entity.get("recordCount") or 0),
                resolved=int(entity.get("resolved") or 0),
                correct=int(entity.get("correct") or 0),
                status_counts=entity.get("statusCounts"),
                position=position,
            )
        )
        report.arms += 1
    report.judges = len(judge_ids)

    for position, observation in enumerate(document.get("observations") or []):
        key = (observation["entity"], observation["slice"], observation["sliceValue"])
        session.merge(
            Observation(
                dataset_id=dataset_id,
                entity_id=observation["entity"],
                metric_key=observation["metric"],
                slice_dim=observation["slice"],
                slice_value=observation["sliceValue"],
                value=observation["value"],
                ci_low=observation["ciLow"],
                ci_high=observation["ciHigh"],
                n=int(observation["n"]),
                slice_records=slice_records.get(key, int(observation["n"])),
                position=position,
            )
        )
        report.observations += 1

    for position, comparison in enumerate(document.get("comparisons") or []):
        session.merge(
            Comparison(
                dataset_id=dataset_id,
                left=comparison["left"],
                right=comparison["right"],
                view=comparison["view"],
                test="mcnemar_exact_two_sided",
                statistic=None,
                p=comparison["pExact"],
                p_holm=comparison["pHolm"],
                n=int(comparison["n"]),
                left_only_correct=int(comparison["leftOnlyCorrect"]),
                right_only_correct=int(comparison["rightOnlyCorrect"]),
                scope="blind_holdout",
                position=position,
            )
        )
        report.comparisons += 1

    for position, aggregate in enumerate(document.get("aggregates") or []):
        session.merge(
            Aggregate(
                id=str(aggregate["key"]),
                dataset_id=dataset_id,
                metric_key=aggregate["metric"],
                method=aggregate["method"],
                over=aggregate["over"],
                derived_from_run_ids=[],
                value=aggregate.get("value"),
                ci_low=aggregate.get("ciLow"),
                ci_high=aggregate.get("ciHigh"),
                n=aggregate.get("n"),
                position=position,
            )
        )
        report.aggregates += 1

    provenance = committed.get("provenance") or {}
    generated_by = provenance.get("wasGeneratedBy") or {}
    session.merge(
        Activity(
            id=str(generated_by.get("id") or f"urn:eval-lab:export:{dataset_id}"),
            type="export",
            agent=generated_by.get("gitCommit"),
            software=provenance.get("generator"),
            commit=provenance.get("commit"),
            started_at=_parse_timestamp(provenance.get("generatedAt")),
            ended_at=_parse_timestamp(provenance.get("generatedAt")),
            used=[entity["path"] for entity in provenance.get("wasDerivedFrom") or []],
            generated=[dataset_id],
        )
    )
    report.activities += 1
    session.flush()


def _judge_id_for(entity: dict[str, Any]) -> str:
    """A judge is a model *on a route*: the same model via two providers differs."""
    raw = f"{entity.get('modelId') or entity['id']}@{entity.get('route') or entity['deployment']}"
    slug = re.sub(r"[^a-z0-9_]+", "_", raw.lower()).strip("_")
    return slug[:128] or entity["id"]


def _judge_row(entity: dict[str, Any], judge_id: str, project_id: str) -> Judge:
    route = str(entity.get("route") or "")
    provider = route.split()[0] if route else None
    return Judge(
        id=judge_id,
        project_id=project_id,
        provider=provider,
        model=entity.get("modelId"),
        route=entity.get("route"),
        family=entity.get("modelFamily"),
        params_b=entity.get("paramsB"),
        deployment=entity["deployment"],
        short_label=entity.get("shortLabel"),
    )


def _config_hash(settings: dict[str, Any] | None) -> str | None:
    if settings is None:
        return None
    canonical = json.dumps(settings, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _experiment_id_for(session: Session, short_id: str) -> str:
    row: Experiment | None = session.scalars(
        select(Experiment).where(Experiment.short_id == short_id)
    ).one_or_none()
    if row is None:
        raise LoadError(f"no experiment with short id {short_id}")
    experiment_id: str = row.id
    return experiment_id


def link_run_entities(
    session: Session,
    document: dict[str, Any],
    run_dirs: dict[Path, str],
    repo_root: Path,
    report: LoadReport,
) -> None:
    """Create the ``run_entities`` links the chart-data ``runs[]`` array implies."""
    for run in document.get("runs") or []:
        artifact = (repo_root / run["path"]).resolve()
        run_dir = _resolve_run_dir(artifact, repo_root)
        run_id = run_dirs.get(run_dir) if run_dir is not None else None
        if run_id is None:
            report.skipped.append(f"{run['path']}: no imported run covers it")
            continue
        session.merge(
            RunEntity(
                run_id=run_id,
                entity_id=run["entity"],
                merge_order=int(run["mergeOrder"]),
                artifact_path=run["path"],
                artifact_sha256=run["sha256"],
            )
        )
        report.run_entities += 1
        size = artifact.stat().st_size if artifact.is_file() else None
        session.merge(
            Artifact(
                run_id=run_id,
                path=run["path"],
                sha256=run["sha256"],
                bytes=size,
                kind="predictions",
            )
        )
        report.artifacts += 1
    session.flush()


def backfill_dataset_fingerprints(
    session: Session, dataset_id: str, run_dirs: dict[Path, str]
) -> None:
    """Copy the blind source-pool fingerprints from a representative run."""
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:  # pragma: no cover - defensive
        return
    for run_id in run_dirs.values():
        run = session.get(Run, run_id)
        if run is None or run.partition != "blind_holdout" or not run.partition_fingerprints:
            continue
        dataset.records_fingerprint = run.partition_fingerprints.get("records_fingerprint")
        dataset.blind_ids_fingerprint = run.partition_fingerprints.get(
            "blind_record_ids_fingerprint"
        )
        dataset.spec_fingerprint = run.partition_fingerprints.get("typed_question_spec_fingerprint")
        break
    session.flush()


# ------------------------------------------------------------------------- main
def clear_dataset_rows(session: Session, dataset_id: str) -> None:
    """Remove the rows a re-load will rebuild, so the loader is idempotent.

    ``observations`` and ``comparisons`` have surrogate keys, so ``merge`` cannot
    update them in place; deleting first is what makes a second load produce the
    same rows as the first.
    """
    dataset = session.get(Dataset, dataset_id)
    run_ids = select(Run.run_id).where(Run.dataset_id == dataset_id)
    session.execute(delete(RunEntity).where(RunEntity.run_id.in_(run_ids)))
    session.execute(delete(Artifact).where(Artifact.run_id.in_(run_ids)))
    session.execute(delete(Observation).where(Observation.dataset_id == dataset_id))
    session.execute(delete(Comparison).where(Comparison.dataset_id == dataset_id))
    session.execute(delete(Aggregate).where(Aggregate.dataset_id == dataset_id))
    session.execute(delete(Arm).where(Arm.dataset_id == dataset_id))
    session.execute(delete(Dimension).where(Dimension.dataset_id == dataset_id))
    session.execute(delete(Level).where(Level.dataset_id == dataset_id))
    if dataset is not None:
        session.execute(delete(Metric).where(Metric.project_id == dataset.project_id))
    session.flush()


def reset_tables(session: Session) -> None:
    """Empty every table (used by ``--reset`` and by the tests)."""
    for table in reversed(LiveBase.metadata.sorted_tables):
        session.execute(delete(table))
    for table in reversed(PrivateBase.metadata.sorted_tables):
        session.execute(delete(table))
    session.flush()


def build_dataset_document(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Recompute the paper's dataset document and load the committed one.

    Returns ``(computed, committed)``.  Raises :class:`LoadError` when the two
    disagree on anything but ``provenance``: the live app must not publish
    numbers the paper does not.
    """
    exporter = _scripts("export_chart_data", repo_root)
    computed = exporter.build_dataset(exporter.git_info())
    committed = _read_json(repo_root / DATASET_FILE)
    mismatch = compare_documents(computed, committed)
    if mismatch:
        raise LoadError(
            f"the recomputed dataset differs from {DATASET_FILE}: {mismatch}. "
            "Refusing to load numbers that disagree with the paper."
        )
    return computed, committed


def compare_documents(computed: dict[str, Any], committed: dict[str, Any]) -> str | None:
    """First difference between two documents, ignoring the provenance block.

    The provenance block is excluded because it records *when and from which
    commit* the export ran, which is not reproducible from a later checkout.
    Everything a reader sees on a chart must match.
    """
    for key in sorted(set(computed) | set(committed)):
        if key == "provenance":
            continue
        if computed.get(key) != committed.get(key):
            return f"key {key!r} differs"
    return None


def load_repository(
    session: Session,
    *,
    repo_root: Path,
    project_id: str = DEFAULT_PROJECT,
    dataset_id: str = DEFAULT_DATASET,
    reset: bool = False,
) -> LoadReport:
    """Import everything.  Idempotent: re-running updates rows in place."""
    repo_root = repo_root.resolve()
    report = LoadReport(project=project_id, dataset=dataset_id)
    if reset:
        reset_tables(session)
    import_project(session, project_id)
    experiments = import_experiments(session, repo_root, project_id)
    report.experiments = len(experiments)
    run_dirs = import_runs(session, repo_root, experiments, dataset_id, report)
    computed, committed = build_dataset_document(repo_root)
    # Rebuild the dataset-scoped rows from scratch, then re-link the runs that
    # ``import_runs`` just wrote.
    clear_dataset_rows(session, dataset_id)
    link_run_entities(session, computed, run_dirs, repo_root, report)
    _decompose_dataset(session, computed, committed, project_id, dataset_id, report)
    backfill_dataset_fingerprints(session, dataset_id, run_dirs)
    return report


def main(argv: list[str] | None = None) -> int:
    from eval_lab_live.config import get_settings
    from eval_lab_live.db import create_db_engine, make_session_factory, session_scope

    parser = argparse.ArgumentParser(description="Backfill the live Eval Lab database.")
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="empty every table first (default: update rows in place)",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    repo_root = args.repo_root or settings.repo_root
    database_url = args.database_url or settings.database_url
    engine = create_db_engine(database_url)
    factory = make_session_factory(engine)
    with session_scope(factory) as session:
        report = load_repository(
            session,
            repo_root=repo_root,
            project_id=args.project,
            dataset_id=args.dataset,
            reset=args.reset,
        )
    print(f"loaded {report.project} / {report.dataset}: {report.summary()}")
    for item in report.skipped:
        print(f"  skipped: {item}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
