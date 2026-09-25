"""Alembic environment.

One database, two schemas (``live`` public-safe, ``private`` never-served).  The
URL comes from :class:`eval_lab_live.config.Settings`, so the same revision
history applies to the compose Postgres, CI's service container and production.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool, text

# ``live/src`` on the path, so ``alembic -c live/alembic.ini`` works from the
# repository root without an install.
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from eval_lab_live.config import get_settings
from eval_lab_live.models import SCHEMA_LIVE, SCHEMA_PRIVATE, LiveBase, PrivateBase

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = [LiveBase.metadata, PrivateBase.metadata]

#: Schemas alembic owns.  Anything else in the database is left alone.
MANAGED_SCHEMAS = (SCHEMA_LIVE, SCHEMA_PRIVATE)


def _database_url() -> str:
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def include_name(name: str | None, type_: str, _parent_names: dict[str, str | None]) -> bool:
    """Ignore tables and schemas that belong to something other than this app."""
    if type_ == "schema":
        return name in MANAGED_SCHEMAS
    return True


def include_object(object_, name, type_, reflected, compare_to) -> bool:  # type: ignore[no-untyped-def]
    """Never autogenerate drops for objects alembic does not own."""
    if type_ == "table" and reflected and compare_to is None:
        return name not in {"alembic_version"}
    return True


def _configure(connection, *, url: str | None = None) -> None:  # type: ignore[no-untyped-def]
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
        include_object=include_object,
        version_table_schema=SCHEMA_LIVE,
        compare_type=True,
        compare_server_default=True,
        url=url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )


def run_migrations_offline() -> None:
    _configure(None, url=_database_url())
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        section, prefix="sqlalchemy.", poolclass=pool.NullPool, future=True
    )
    with connectable.connect() as connection:
        # A fresh database has neither schema; create them before alembic looks
        # for its version table inside ``live``.
        for schema in MANAGED_SCHEMAS:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        connection.commit()
        _configure(connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
