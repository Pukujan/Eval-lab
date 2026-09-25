# Image for the live backend (API, migrations and loader).
#
# Build from the repository root, because the loader reads the same committed
# artifacts the research scripts do:
#
#     docker build -f live/docker/Dockerfile -t eval-lab-live .
#
# The virtualenv lives outside /app so a bind mount of the repository (which is
# how `live/docker-compose.yml` runs it) does not shadow it.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir "uv>=0.5"

WORKDIR /app

# Only what the install needs, so the dependency layer caches across code edits.
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY live ./live

# `--locked` makes the build fail on a stale lockfile rather than resolving
# something CI never saw.  `dev` is not an extra here: the runtime image has no
# test dependencies.
RUN uv sync --locked --extra live --no-dev

EXPOSE 8000

# The API only ever connects as the read-only role; compose sets the URL.
CMD ["uvicorn", "eval_lab_live.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
