#!/usr/bin/env bash
# Create the two database roles the live app runs as.
#
# Runs once, as the superuser, on first `docker compose up` (the Postgres entrypoint
# executes everything in /docker-entrypoint-initdb.d).  Passwords are dev-only
# defaults, overridable from the environment; nothing here is used in production.
#
#   evallab_public_ro  the read API.  SELECT on `live`, nothing at all on `private`.
#   evallab_ingest_rw  the loader / ingest service.  DML on both schemas, no DDL.
#
# The grants themselves live in the Alembic revision `0002_roles`, so they are
# applied the same way on a fresh database and on an existing one.
set -euo pipefail

PUBLIC_RO_PASSWORD="${EVALLAB_PUBLIC_RO_PASSWORD:-evallab_public_ro}"
INGEST_RW_PASSWORD="${EVALLAB_INGEST_RW_PASSWORD:-evallab_ingest_rw}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v dbname="$POSTGRES_DB" \
  -v public_ro_password="$PUBLIC_RO_PASSWORD" \
  -v ingest_rw_password="$INGEST_RW_PASSWORD" <<-'SQL'
    -- `\gexec` keeps this idempotent: the script may be re-run by hand.
    SELECT format('CREATE ROLE evallab_public_ro LOGIN PASSWORD %L', :'public_ro_password')
    WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'evallab_public_ro')
    \gexec

    SELECT format('CREATE ROLE evallab_ingest_rw LOGIN PASSWORD %L', :'ingest_rw_password')
    WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'evallab_ingest_rw')
    \gexec

    GRANT CONNECT ON DATABASE :"dbname" TO evallab_public_ro, evallab_ingest_rw;

    -- Neither role may create objects in the default schema, and PUBLIC gets
    -- nothing.  The `live`/`private` schemas are created by the first Alembic
    -- revision, which also revokes `private` from PUBLIC.
    REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SQL

echo "bootstrap: created evallab_public_ro and evallab_ingest_rw"
