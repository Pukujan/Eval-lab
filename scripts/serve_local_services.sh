#!/usr/bin/env bash
# Start Phoenix and the LiteLLM Proxy as local processes.
#
# The supported way to run these is `make up` (Docker Compose, digest-pinned).
# This script exists for environments where container images cannot be pulled —
# it runs the SAME pinned package versions in their own virtualenvs, mirroring
# the one-service-per-environment split the compose file uses (ADR-0010).
#
# It cannot start Temporal: the dev server is a binary fetched from
# temporal.download, which is not a pip package. Without it, runs take the
# degraded local path and are labelled NON_DURABLE_EXECUTION (ADR-0006).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VAR_DIR="${VAR_DIR:-$ROOT/var}"
mkdir -p "$VAR_DIR/phoenix" "$VAR_DIR/logs"

start_phoenix() {
  if [[ ! -x "$ROOT/.venv-phoenix/bin/phoenix" ]]; then
    echo "Phoenix venv missing. Create it with:"
    echo "  uv venv --python 3.12 .venv-phoenix && \\"
    echo "  uv pip install --python .venv-phoenix/bin/python arize-phoenix==19.10.0"
    return 1
  fi
  echo "starting phoenix on :6006 (sqlite at $VAR_DIR/phoenix/phoenix.db)"
  PHOENIX_WORKING_DIR="$VAR_DIR/phoenix" \
  PHOENIX_SQL_DATABASE_URL="sqlite:///$VAR_DIR/phoenix/phoenix.db" \
  PHOENIX_PORT=6006 \
  PHOENIX_GRPC_PORT=4317 \
  PHOENIX_ENABLE_PROMETHEUS=false \
    nohup "$ROOT/.venv-phoenix/bin/phoenix" serve \
    > "$VAR_DIR/logs/phoenix.log" 2>&1 &
}

start_litellm() {
  if [[ ! -x "$ROOT/.venv-litellm/bin/litellm" ]]; then
    echo "LiteLLM venv missing. Create it with:"
    echo "  uv venv --python 3.12 .venv-litellm && \\"
    echo "  uv pip install --python .venv-litellm/bin/python 'litellm[proxy]==1.94.0'"
    return 1
  fi
  echo "starting litellm proxy on :4000"
  # The custom provider handler is imported by dotted path, so the application
  # package must be importable by the proxy process.
  PYTHONPATH="$ROOT" \
  LITELLM_MASTER_KEY="${LITELLM_MASTER_KEY:-sk-local-mock-only}" \
    nohup "$ROOT/.venv-litellm/bin/litellm" \
    --config "$ROOT/config/litellm-config.yaml" --port 4000 --num_workers 1 \
    > "$VAR_DIR/logs/litellm.log" 2>&1 &
}

wait_for() {
  local name="$1" url="$2" attempts="${3:-60}"
  for _ in $(seq 1 "$attempts"); do
    if curl -fsS --noproxy '*' "$url" >/dev/null 2>&1; then
      echo "  $name ready"
      return 0
    fi
    sleep 2
  done
  echo "  $name did NOT become ready; see $VAR_DIR/logs/"
  return 1
}

start_phoenix || true
start_litellm || true

echo "waiting for readiness..."
wait_for phoenix "http://localhost:6006/healthz" || true
wait_for litellm "http://localhost:4000/health/readiness" || true

echo
echo "Phoenix UI : http://localhost:6006"
echo "LiteLLM    : http://localhost:4000"
echo "Temporal   : NOT started (dev-server binary unavailable offline)"
