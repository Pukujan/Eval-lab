"""Runtime settings for the live backend.

Everything is read from the environment with the ``EVALLAB_LIVE_`` prefix, so the
same image runs as the public API (``EVALLAB_LIVE_DATABASE_URL`` pointing at the
``evallab_public_ro`` role) or as the loader/ingest job (owner role).

There are no secrets in this file and none in the repository: ``live/.env`` is
git-ignored and only the compose file reads it.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Slice-level suppression threshold for non-public partitions (architecture
#: doc section 11).  A slice whose *population* is smaller than this is dropped
#: from public responses entirely, so filters cannot be used to narrow a blind
#: partition down to a handful of items.
DEFAULT_MIN_SLICE_RECORDS = 20

#: Public cache header for live (non-immutable) endpoints.  Cloudflare/Vercel
#: both honour ``CDN-Cache-Control``; the short max-age keeps ingest visible.
LIVE_CACHE_CONTROL = "public, max-age=0, stale-while-revalidate=300"
LIVE_CDN_CACHE_CONTROL = "max-age=30"
IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"


class Settings(BaseSettings):
    """Environment-driven configuration."""

    model_config = SettingsConfigDict(
        env_prefix="EVALLAB_LIVE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    #: SQLAlchemy URL.  The public API must use a role that has no grant on the
    #: ``private`` schema; the default is that read-only role.
    database_url: str = Field(
        default="postgresql+psycopg://evallab_public_ro:evallab_public_ro@localhost:5432/evallab"
    )
    #: Repository root used by the loader to find ``experiments/`` and
    #: ``paper/data/``.  Defaults to the checkout that contains this file.
    repo_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3])
    #: Name of the project row the read API serves by default.
    default_project: str = "eval-lab"
    #: Dataset served when a request omits ``?dataset=``.  Matches
    #: ``export_chart_data.DATASET_ID`` so the API's default document is the one
    #: the papers embed.
    default_project_dataset: str = "eval-lab/judges-blind-760"
    #: Emitted by ``/status`` and ``/version`` so the frontend can show which
    #: build it is talking to.  The image sets it from the git SHA.
    build_commit: str = "unknown"
    service_version: str = "0.1.0"
    #: Suppress slices whose population is below this on non-public partitions.
    min_slice_records: int = DEFAULT_MIN_SLICE_RECORDS
    #: Hard cap on entities returned by one document request.
    max_entities: int = 200
    #: Hard cap on observations returned by one document request.
    max_observations: int = 20000

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith(("sqlite:", "sqlite+"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
