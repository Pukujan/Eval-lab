"""FastAPI application for the public read API (TASK-0060 phase 2)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from eval_lab_live import __version__, chartdata
from eval_lab_live import repository as repo
from eval_lab_live.config import (
    IMMUTABLE_CACHE_CONTROL,
    LIVE_CACHE_CONTROL,
    LIVE_CDN_CACHE_CONTROL,
    Settings,
    get_settings,
)
from eval_lab_live.db import create_db_engine, make_session_factory
from eval_lab_live.models import (
    Activity,
    Arm,
    Dataset,
    Observation,
    Run,
    RunEntity,
)
from eval_lab_live.sanitize import DENYLISTED_KEYS

NO_STORE = "no-store"


# --------------------------------------------------------------------- schemas
class HealthResponse(BaseModel):
    ok: bool
    service: str
    version: str


class VersionResponse(BaseModel):
    service: str
    version: str
    apiVersion: str
    schemaVersion: str
    buildCommit: str
    evalLabCommit: str | None


class StatusResponse(BaseModel):
    ok: bool
    db: bool
    service: str
    version: str
    apiVersion: str
    schemaVersion: str
    runsTotal: int
    datasetsTotal: int
    lastRunAt: str | None
    lastIngestAt: str | None
    minSliceRecords: int


class DatasetSummary(BaseModel):
    id: str
    name: str
    version: str
    experimentId: str | None
    recordCount: int
    blindCount: int
    publicCount: int
    title: str | None
    partition: str | None
    splitPolicy: str | None
    levels: list[str]
    entityCount: int
    observationCount: int


class RunSummary(BaseModel):
    runId: str
    experimentId: str
    partition: str | None
    status: str | None
    recordCount: int | None
    resolvedCount: int | None
    statusCounts: dict[str, Any] | None
    finishedAt: str | None
    resultsPath: str | None
    resultsSha256: str | None
    artifacts: list[dict[str, Any]] = []
    entities: list[str] = []


# ------------------------------------------------------------------ dependencies
def get_session(request: Request) -> Iterator[Session]:
    factory = request.app.state.session_factory
    session: Session = factory()
    try:
        yield session
    finally:
        session.close()


SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    formatted: str = value.isoformat()
    return formatted


def _dataset_or_404(session: Session, dataset_id: str | None, settings: Settings) -> Dataset:
    return repo.get_dataset(session, dataset_id or settings.default_project_dataset)


def _min_slice_records(dataset: Dataset, settings: Settings) -> int:
    """The min-slice threshold for one dataset.

    ``datasets.min_slice_records`` overrides the configured default.  A dataset
    whose records are already public sets it to 0, because suppressing a slice
    there would hide a number the papers publish -- see
    ``loader.PUBLISHED_DATASETS``.  Everything else gets the threshold from
    ``Settings.min_slice_records``.
    """
    override: int | None = dataset.min_slice_records
    if override is not None:
        return override
    configured: int = settings.min_slice_records
    return configured


def _filters(
    entity: list[str] | None,
    experiment: list[str] | None,
    deployment: list[str] | None,
    model_family: list[str] | None,
    metric: list[str] | None,
    slice_: list[str] | None,
    slice_value: list[str] | None,
    headline: bool,
    level: str | None,
) -> repo.DocumentFilters:
    if level is not None and level not in repo.LEVELS:
        raise repo.InvalidQuery(
            f"unknown level {level!r}; expected one of {', '.join(repo.LEVELS)}"
        )
    return repo.DocumentFilters(
        entities=tuple(entity or ()),
        experiments=tuple(experiment or ()),
        deployments=tuple(deployment or ()),
        model_families=tuple(model_family or ()),
        metrics=tuple(metric or ()),
        slices=tuple(slice_ or ()),
        slice_values=tuple(slice_value or ()),
        headline_only=headline,
        level=level,
    )


def _document(
    session: Session, dataset: Dataset, filters: repo.DocumentFilters, settings: Settings
) -> dict[str, Any]:
    return chartdata.build_document(
        session,
        dataset,
        filters=filters,
        min_slice_records=_min_slice_records(dataset, settings),
        max_entities=settings.max_entities,
        max_observations=settings.max_observations,
    )


# ----------------------------------------------------------------------- routers
def build_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.get("/health", response_model=HealthResponse, tags=["meta"])
    def health(settings: SettingsDep) -> HealthResponse:
        """Liveness only: no database access, so it stays up during a DB blip."""
        return HealthResponse(ok=True, service="eval-lab-live", version=settings.service_version)

    @router.get("/version", response_model=VersionResponse, tags=["meta"])
    def version(session: SessionDep, settings: SettingsDep) -> VersionResponse:
        commit = session.scalars(
            select(Dataset.provenance).where(Dataset.id == settings.default_project_dataset)
        ).one_or_none()
        eval_lab_commit = (commit or {}).get("commit") if isinstance(commit, dict) else None
        return VersionResponse(
            service="eval-lab-live",
            version=settings.service_version,
            apiVersion="v1",
            schemaVersion=chartdata.SCHEMA_VERSION,
            buildCommit=settings.build_commit,
            evalLabCommit=eval_lab_commit,
        )

    @router.get("/status", response_model=StatusResponse, tags=["meta"])
    def status(session: SessionDep, settings: SettingsDep) -> StatusResponse:
        """Drives the frontend's offline banner.

        A database the API cannot read is a *degraded* service, not a broken one:
        the SPA falls back to a committed snapshot, so this returns 200 with
        ``ok: false`` instead of a 500.
        """
        try:
            runs_total = session.scalar(select(func.count()).select_from(Run)) or 0
            datasets_total = session.scalar(select(func.count()).select_from(Dataset)) or 0
            last_run = session.scalar(select(func.max(Run.finished_at)))
            db_ok = True
        except SQLAlchemyError:  # pragma: no cover - exercised by the offline test
            runs_total = datasets_total = 0
            last_run = None
            db_ok = False
        return StatusResponse(
            ok=db_ok,
            db=db_ok,
            service="eval-lab-live",
            version=settings.service_version,
            apiVersion="v1",
            schemaVersion=chartdata.SCHEMA_VERSION,
            runsTotal=runs_total,
            datasetsTotal=datasets_total,
            lastRunAt=_iso(last_run),
            lastIngestAt=None,
            minSliceRecords=settings.min_slice_records,
        )

    @router.get("/projects", tags=["catalog"])
    def projects(session: SessionDep) -> list[dict[str, Any]]:
        return [
            {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "createdAt": _iso(project.created_at),
            }
            for project in repo.list_projects(session)
        ]

    @router.get("/datasets", response_model=list[DatasetSummary], tags=["catalog"])
    def datasets(session: SessionDep, project: str | None = None) -> list[DatasetSummary]:
        summaries = []
        for dataset in repo.list_datasets(session, project):
            entity_count = session.scalar(
                select(func.count()).select_from(Arm).where(Arm.dataset_id == dataset.id)
            )
            observation_count = session.scalar(
                select(func.count())
                .select_from(Observation)
                .where(Observation.dataset_id == dataset.id)
            )
            summaries.append(
                DatasetSummary(
                    id=dataset.id,
                    name=dataset.name,
                    version=dataset.version,
                    experimentId=dataset.experiment_id,
                    recordCount=dataset.record_count,
                    blindCount=dataset.blind_count,
                    publicCount=dataset.public_count,
                    title=dataset.title,
                    partition=(dataset.population or {}).get("partition"),
                    splitPolicy=dataset.split_policy,
                    levels=[level.key for level in repo.list_levels(session, dataset.id)],
                    entityCount=entity_count or 0,
                    observationCount=observation_count or 0,
                )
            )
        return summaries

    @router.get("/experiments", tags=["catalog"])
    def experiments(session: SessionDep, dataset: str | None = None) -> list[dict[str, Any]]:
        return [
            {
                "id": experiment.id,
                "shortId": experiment.short_id,
                "directory": experiment.directory,
                "title": experiment.title,
                "status": experiment.status,
                "createdAt": experiment.created_at,
                "codeCommit": experiment.code_commit,
            }
            for experiment in repo.list_experiments(session, dataset)
        ]

    @router.get("/judges", tags=["catalog"])
    def judges(session: SessionDep, dataset: str | None = None) -> list[dict[str, Any]]:
        return [
            {
                "id": judge.id,
                "provider": judge.provider,
                "model": judge.model,
                "route": judge.route,
                "family": judge.family,
                "paramsB": judge.params_b,
                "deployment": judge.deployment,
                "shortLabel": judge.short_label,
            }
            for judge in repo.list_judges(session, dataset)
        ]

    @router.get("/metrics", tags=["catalog"])
    def metrics(session: SessionDep, dataset: str | None = None) -> list[dict[str, Any]]:
        return [
            {
                "key": metric.key,
                "label": metric.label,
                "unit": metric.unit,
                "format": metric.format,
                "better": metric.better,
                "interval": metric.interval_method,
                "definition": metric.definition,
                "n": metric.n_label,
            }
            for metric in repo.list_metrics(session, dataset)
        ]

    @router.get("/datasets/{dataset_id}", tags=["documents"])
    def dataset_document(
        dataset_id: str,
        session: SessionDep,
        settings: SettingsDep,
        response: Response,
        entity: Annotated[list[str] | None, Query()] = None,
        experiment: Annotated[list[str] | None, Query()] = None,
        deployment: Annotated[list[str] | None, Query()] = None,
        model_family: Annotated[list[str] | None, Query()] = None,
        metric: Annotated[list[str] | None, Query()] = None,
        slice: Annotated[list[str] | None, Query()] = None,
        slice_value: Annotated[list[str] | None, Query()] = None,
        headline: bool = False,
        level: str | None = None,
    ) -> dict[str, Any]:
        """The full chart-data v1 document, or one level of it."""
        dataset = repo.get_dataset(session, dataset_id)
        filters = _filters(
            entity,
            experiment,
            deployment,
            model_family,
            metric,
            slice,
            slice_value,
            headline,
            level,
        )
        document = _document(session, dataset, filters, settings)
        response.headers["Cache-Control"] = LIVE_CACHE_CONTROL
        response.headers["CDN-Cache-Control"] = LIVE_CDN_CACHE_CONTROL
        response.headers["Vercel-Cache-Tag"] = f"eval-lab-{dataset.id}"
        return document

    @router.get("/datasets/{dataset_id}/entities", tags=["documents"])
    def dataset_entities(
        dataset_id: str,
        session: SessionDep,
        settings: SettingsDep,
        headline: bool = False,
    ) -> list[dict[str, Any]]:
        dataset = repo.get_dataset(session, dataset_id)
        filters = repo.DocumentFilters(headline_only=headline)
        arms = repo.list_arms(session, dataset.id, filters, limit=settings.max_entities)
        return [chartdata.entity_document(arm) for arm in arms]

    @router.get("/datasets/{dataset_id}/observations", tags=["documents"])
    def dataset_observations(
        dataset_id: str,
        session: SessionDep,
        settings: SettingsDep,
        entity: Annotated[list[str] | None, Query()] = None,
        metric: Annotated[list[str] | None, Query()] = None,
        slice: Annotated[list[str] | None, Query()] = None,
        slice_value: Annotated[list[str] | None, Query()] = None,
    ) -> list[dict[str, Any]]:
        dataset = repo.get_dataset(session, dataset_id)
        filters = _filters(entity, None, None, None, metric, slice, slice_value, False, None)
        arms = repo.list_arms(session, dataset.id, filters, limit=settings.max_entities)
        observations = repo.list_observations(
            session,
            dataset.id,
            [arm.id for arm in arms],
            filters,
            min_slice_records=_min_slice_records(dataset, settings),
            level=None,
            limit=settings.max_observations,
        )
        return [chartdata.observation_document(item) for item in observations]

    @router.get("/datasets/{dataset_id}/levels", tags=["documents"])
    def dataset_levels(dataset_id: str, session: SessionDep) -> list[dict[str, Any]]:
        repo.get_dataset(session, dataset_id)
        return [chartdata.level_document(level) for level in repo.list_levels(session, dataset_id)]

    @router.get("/datasets/{dataset_id}/dimensions", tags=["documents"])
    def dataset_dimensions(dataset_id: str, session: SessionDep) -> list[dict[str, Any]]:
        repo.get_dataset(session, dataset_id)
        return [
            chartdata.dimension_document(dimension)
            for dimension in repo.list_dimensions(session, dataset_id)
        ]

    @router.get("/datasets/{dataset_id}/filters", tags=["documents"])
    def dataset_filters(dataset_id: str, session: SessionDep) -> dict[str, Any]:
        repo.get_dataset(session, dataset_id)
        return repo.facets(session, dataset_id).__dict__

    @router.get("/leaderboard", tags=["documents"])
    def leaderboard(
        session: SessionDep,
        settings: SettingsDep,
        response: Response,
        dataset: str | None = None,
        metric: Annotated[list[str] | None, Query()] = None,
        level: str = "summary",
        headline: bool = False,
    ) -> dict[str, Any]:
        """Ranked entities at one level.  Same document shape as the paper's."""
        dataset_row = _dataset_or_404(session, dataset, settings)
        filters = _filters(None, None, None, None, metric, None, None, headline, level)
        document = _document(session, dataset_row, filters, settings)
        response.headers["Cache-Control"] = LIVE_CACHE_CONTROL
        response.headers["CDN-Cache-Control"] = LIVE_CDN_CACHE_CONTROL
        response.headers["Vercel-Cache-Tag"] = f"eval-lab-{dataset_row.id}"
        return document

    @router.get("/explore", tags=["documents"])
    def explore(
        session: SessionDep,
        settings: SettingsDep,
        response: Response,
        dataset: str | None = None,
        entity: Annotated[list[str] | None, Query()] = None,
        experiment: Annotated[list[str] | None, Query()] = None,
        deployment: Annotated[list[str] | None, Query()] = None,
        model_family: Annotated[list[str] | None, Query()] = None,
        metric: Annotated[list[str] | None, Query()] = None,
        slice: Annotated[list[str] | None, Query()] = None,
        slice_value: Annotated[list[str] | None, Query()] = None,
        headline: bool = False,
        level: str | None = None,
    ) -> dict[str, Any]:
        dataset_row = _dataset_or_404(session, dataset, settings)
        filters = _filters(
            entity,
            experiment,
            deployment,
            model_family,
            metric,
            slice,
            slice_value,
            headline,
            level,
        )
        document = _document(session, dataset_row, filters, settings)
        response.headers["Cache-Control"] = LIVE_CACHE_CONTROL
        response.headers["CDN-Cache-Control"] = LIVE_CDN_CACHE_CONTROL
        response.headers["Vercel-Cache-Tag"] = f"eval-lab-{dataset_row.id}"
        return document

    @router.get("/runs", tags=["runs"])
    def runs(session: SessionDep, dataset: str | None = None) -> list[dict[str, Any]]:
        return [_run_summary(run) for run in repo.list_runs(session, dataset)]

    @router.get("/runs/{run_id}", response_model=RunSummary, tags=["runs"])
    def run_detail(run_id: str, session: SessionDep) -> RunSummary:
        run = repo.get_run(session, run_id)
        summary = _run_summary(run)
        summary["artifacts"] = [
            {
                "path": artifact.path,
                "sha256": artifact.sha256,
                "bytes": artifact.bytes,
                "kind": artifact.kind,
            }
            for artifact in repo.list_artifacts(session, run_id)
        ]
        summary["entities"] = list(
            session.scalars(
                select(RunEntity.entity_id)
                .where(RunEntity.run_id == run_id)
                .order_by(RunEntity.merge_order)
            ).all()
        )
        return RunSummary(**summary)

    @router.get("/runs/{run_id}/provenance.jsonld", tags=["runs"])
    def run_provenance(run_id: str, session: SessionDep, settings: SettingsDep) -> dict[str, Any]:
        """PROV-O JSON-LD for one run: the activity, its software agent and outputs."""
        run = repo.get_run(session, run_id)
        dataset = repo.get_dataset(session, run.dataset_id)
        activity = session.get(Activity, f"urn:eval-lab:run:{run_id}")
        context = dict(dataset.context or {})
        context.setdefault("prov", "http://www.w3.org/ns/prov#")
        context.setdefault("schema", "https://schema.org/")
        graph: list[dict[str, Any]] = []
        if activity is not None:
            graph.append(
                {
                    "@id": activity.id,
                    "@type": "prov:Activity",
                    "prov:startedAtTime": _iso(activity.started_at),
                    "prov:endedAtTime": _iso(activity.ended_at),
                    "prov:used": [{"@id": _blob(settings, path)} for path in (activity.used or [])],
                    "prov:wasAssociatedWith": {
                        "@id": f"urn:eval-lab:runner:{run.experiment_id}",
                        "@type": "prov:SoftwareAgent",
                        "schema:name": activity.software or "eval-lab runner",
                        "ev:gitCommit": activity.commit,
                    },
                    "ev:generated": activity.generated or [],
                }
            )
        graph.append(
            {
                "@id": f"urn:eval-lab:run:{run_id}",
                "@type": ["prov:Entity", "schema:Dataset"],
                "schema:name": run_id,
                "ev:experimentId": run.experiment_id,
                "ev:partition": run.partition,
                "ev:recordCount": run.record_count,
                "ev:resultsPath": run.results_path,
                "ev:sha256": run.results_sha256,
                "prov:wasGeneratedBy": {"@id": f"urn:eval-lab:run:{run_id}"},
                "prov:wasDerivedFrom": [
                    {"@id": _blob(settings, artifact.path), "ev:sha256": artifact.sha256}
                    for artifact in repo.list_artifacts(session, run_id)
                ],
            }
        )
        return {"@context": context, "@graph": graph}

    @router.get("/snapshots", tags=["snapshots"])
    def snapshots(session: SessionDep) -> list[dict[str, Any]]:
        return [
            {
                "id": snapshot.id,
                "createdAt": _iso(snapshot.created_at),
                "schemaVersion": snapshot.schema_version,
                "sha256": snapshot.sha256,
                "allRunsCommitted": snapshot.all_runs_committed,
                "evalLabCommit": snapshot.eval_lab_commit,
            }
            for snapshot in repo.list_snapshots(session)
        ]

    @router.get("/snapshots/{snapshot_id}", tags=["snapshots"])
    def snapshot_document(
        snapshot_id: str, session: SessionDep, response: Response
    ) -> dict[str, Any]:
        snapshot = repo.get_snapshot(session, snapshot_id)
        response.headers["Cache-Control"] = IMMUTABLE_CACHE_CONTROL
        return dict(snapshot.content or {})

    return router


def _run_summary(run: Run) -> dict[str, Any]:
    return {
        "runId": run.run_id,
        "experimentId": run.experiment_id,
        "partition": run.partition,
        "status": run.status,
        "recordCount": run.record_count,
        "resolvedCount": run.resolved_count,
        "statusCounts": run.status_counts,
        "finishedAt": _iso(run.finished_at),
        "resultsPath": run.results_path,
        "resultsSha256": run.results_sha256,
        "artifacts": [],
    }


def _blob(settings: Settings, path: str) -> str:
    commit = settings.build_commit if settings.build_commit != "unknown" else "main"
    return f"https://github.com/Pukujan/Eval-lab/blob/{commit}/{path}"


def create_app(
    settings: Settings | None = None,
    *,
    session_factory: Any | None = None,
) -> FastAPI:
    """Build the app.  Tests pass a session factory bound to SQLite."""
    resolved = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # pragma: no cover - exercised via TestClient
        if app.state.session_factory is None:
            engine = create_db_engine(resolved.database_url)
            app.state.session_factory = make_session_factory(engine)
            app.state.engine = engine
        yield

    app = FastAPI(
        title="Eval Lab live API",
        version=__version__,
        description=(
            "Read-only public API over every committed Eval Lab run. Chart endpoints return "
            "research-chart-data v1 documents, the same shape the papers embed."
        ),
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.state.settings = resolved
    app.state.session_factory = session_factory
    app.include_router(build_router())

    @app.exception_handler(repo.NotFound)
    async def _not_found(_request: Request, exc: repo.NotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(repo.InvalidQuery)
    async def _invalid(_request: Request, exc: repo.InvalidQuery) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.middleware("http")
    async def _cache_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        path = request.url.path
        if "cache-control" not in {key.lower() for key in response.headers}:
            if path.endswith(("/status", "/health", "/version")):
                response.headers["Cache-Control"] = NO_STORE
            elif path.startswith("/api/v1/snapshots/"):
                response.headers["Cache-Control"] = IMMUTABLE_CACHE_CONTROL
            else:
                response.headers["Cache-Control"] = LIVE_CACHE_CONTROL
                response.headers["CDN-Cache-Control"] = LIVE_CDN_CACHE_CONTROL
        return response

    @app.get("/health", include_in_schema=False)
    async def root_health() -> dict[str, Any]:
        return {"ok": True, "service": "eval-lab-live", "version": resolved.service_version}

    return app


__all__ = ["DENYLISTED_KEYS", "build_router", "create_app"]
