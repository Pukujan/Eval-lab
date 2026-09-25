"""Role separation: the public read role can see ``live`` and never ``private``.

This is the database-level half of the leakage control in
``docs/architecture/live-app.md`` section 11.  The API connects as
``evallab_public_ro``; that role has ``SELECT`` on the public-safe schema and no
privilege whatsoever on the per-record schema, so a bug in a query cannot leak
per-record rows -- the server refuses.  ``live/tests/test_roles_pg.py`` asserts
it against a real Postgres.

Roles are *created* by the deployment (``live/docker/bootstrap/10-roles.sql`` and
the CI service container), because creating roles needs a superuser.  This
revision only grants, and it skips a role that does not exist so a single-role
development database still migrates cleanly.

Revision ID: 0002_roles
Revises: 0001_initial
Create Date: 2026-09-24
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_roles"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LIVE = "live"
PRIVATE = "private"
PUBLIC_RO = "evallab_public_ro"
INGEST_RW = "evallab_ingest_rw"

#: ``GRANT``/``REVOKE`` are skipped for a role that does not exist yet.
_GRANTS = f"""
DO $$
DECLARE
    role_name text;
BEGIN
    FOREACH role_name IN ARRAY ARRAY['{PUBLIC_RO}', '{INGEST_RW}'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
            EXECUTE format('GRANT USAGE ON SCHEMA {LIVE} TO %I', role_name);
        END IF;
    END LOOP;
END
$$;

-- Nobody reaches the per-record schema through PUBLIC.
REVOKE ALL ON SCHEMA {PRIVATE} FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA {PRIVATE} FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA {PRIVATE} FROM PUBLIC;
"""

#: The public role: read the public-safe schema, and nothing else, ever.
_READ_ONLY = f"""
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{PUBLIC_RO}') THEN
        EXECUTE 'REVOKE ALL ON SCHEMA {PRIVATE} FROM {PUBLIC_RO}';
        EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA {PRIVATE} FROM {PUBLIC_RO}';
        EXECUTE 'REVOKE ALL ON ALL SEQUENCES IN SCHEMA {PRIVATE} FROM {PUBLIC_RO}';
        EXECUTE 'REVOKE CREATE ON SCHEMA {LIVE} FROM {PUBLIC_RO}';
        EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA {LIVE} FROM {PUBLIC_RO}';
        EXECUTE 'GRANT SELECT ON ALL TABLES IN SCHEMA {LIVE} TO {PUBLIC_RO}';
        EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA {LIVE} '
                'GRANT SELECT ON TABLES TO {PUBLIC_RO}';
    END IF;
END
$$;
"""

#: The loader/ingest role: full DML on both schemas, still no DDL.
_INGEST = f"""
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{INGEST_RW}') THEN
        EXECUTE 'GRANT USAGE, CREATE ON SCHEMA {LIVE} TO {INGEST_RW}';
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {LIVE} TO {INGEST_RW}';
        EXECUTE 'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {LIVE} TO {INGEST_RW}';
        EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA {LIVE} '
                'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {INGEST_RW}';
        EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA {LIVE} '
                'GRANT USAGE, SELECT ON SEQUENCES TO {INGEST_RW}';
        EXECUTE 'GRANT USAGE ON SCHEMA {PRIVATE} TO {INGEST_RW}';
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {PRIVATE} TO {INGEST_RW}';
        EXECUTE 'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {PRIVATE} TO {INGEST_RW}';
        EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA {PRIVATE} '
                'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {INGEST_RW}';
    END IF;
END
$$;
"""


def upgrade() -> None:
    for statement in (_GRANTS, _READ_ONLY, _INGEST):
        op.execute(statement)


def downgrade() -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{PUBLIC_RO}') THEN
                EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA {LIVE} FROM {PUBLIC_RO}';
                EXECUTE 'REVOKE ALL ON SCHEMA {LIVE} FROM {PUBLIC_RO}';
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{INGEST_RW}') THEN
                EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA {LIVE} FROM {INGEST_RW}';
                EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA {PRIVATE} FROM {INGEST_RW}';
                EXECUTE 'REVOKE ALL ON SCHEMA {LIVE} FROM {INGEST_RW}';
                EXECUTE 'REVOKE ALL ON SCHEMA {PRIVATE} FROM {INGEST_RW}';
            END IF;
        END
        $$;
        """
    )
