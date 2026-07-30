# Worker image for the reliability walking skeleton.
# Base image is digest-pinned; see docs/dependency-dossier.md.
FROM python:3.12.11-slim@sha256:47ae396f09c1303b8653019811a8498470603d7ffefc29cb07c88f1f8cb3d19f

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

# Dependencies first so a source change does not invalidate the install layer.
COPY pyproject.toml README.md ./
COPY app ./app
# The dev extra is required at runtime, not merely for development: verifying a
# candidate runs the fixture's pytest suites and a Hypothesis property inside the
# working copy, so pytest and hypothesis must exist in this image.
RUN pip install --no-cache-dir ".[dev]"

COPY fixtures ./fixtures
COPY evals ./evals
COPY config ./config
COPY scripts ./scripts

# Run as an unprivileged user: the worker executes fixture tests in subprocesses
# and has no reason to hold root (threat model T-4).
RUN useradd --create-home --uid 10001 runner \
    && mkdir -p /var/rws \
    && chown -R runner:runner /srv /var/rws
USER runner

CMD ["python", "-m", "app.worker_entrypoint"]
