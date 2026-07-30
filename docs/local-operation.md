# Local operation

How to run the stack, what each service is for, and what to do when one of them
does not come up.

Everything here works without paid credentials. The model path is the
deterministic mock provider registered through LiteLLM's `custom_provider_map`.

## The stack

| Service | Image (digest-pinned) | Ports | Purpose |
|---|---|---|---|
| `temporal` | `temporalio/temporal:1.8.1` | 7233 (gRPC), 8233 (Web UI) | Dev server + Web UI + SQLite persistence |
| `phoenix` | `arizephoenix/phoenix:version-19.10.0` | 6006 (UI + OTLP/HTTP), 4317 (OTLP/gRPC) | Trace collection, storage, UI |
| `litellm` | `ghcr.io/berriai/litellm:v1.94.0` | 4000 | Model gateway; serves the three mocks |
| `worker` | built from `Dockerfile` (`python:3.12.11-slim`) | — | Long-lived Temporal worker |

No PostgreSQL, Redis, Prometheus, Grafana or Kubernetes. Temporal's `start-dev`
persists to a SQLite file on a named volume, which is why no separate database
exists (ADR-0005).

## Commands

```bash
make setup     # install pinned dependencies into .venv
make up        # start everything, wait for health, then run make health
make health    # verify every service through the endpoint Compose health-checks
make demo      # the complete walking-skeleton scenario, both candidates
make test      # deterministic tests; needs no services and no credentials
make eval      # Inspect AI + Promptfoo evaluations
make traces    # Phoenix URL and recent trace identifiers
make down      # stop the stack
make clean     # stop, remove volumes, delete generated state
```

### Durability verification (needs a running stack)

```bash
python scripts/verify_compose.py --phase clean   # DNS, health, deps, volumes
python scripts/init_state.py                     # stores + namespace
python scripts/verify_durability.py              # SIGKILL a worker, resume, recover
python scripts/verify_retry.py                   # retries from real history
python scripts/verify_timeout.py                 # timeout -> infrastructure_failure
python scripts/verify_replay.py                  # replay + incompatible-variant detection
python scripts/verify_phoenix_trace.py           # every required span present
python scripts/verify_persistence.py             # run after a stop/up cycle
python scripts/build_completion_manifest.py      # machine-readable summary
```

Each writes evidence JSON (and, where relevant, the raw Temporal history) to
`$EVIDENCE_DIR`, defaulting to `var/evidence/`. Each exits non-zero if its claim
cannot be evidenced.

`scripts/verify_durability.py` must run before `scripts/verify_replay.py` —
replay needs a real history to replay.

## Startup order

`worker` declares `depends_on: {temporal, phoenix, litellm}` with
`condition: service_healthy`, so it does not start until all three report healthy.
`make up` uses `--wait`, which blocks until every health check passes.

Health checks, and why each is what it is:

| Service | Check | Why |
|---|---|---|
| `temporal` | `temporal operator cluster health` | The CLI ships in the image, so this exercises the real cluster health RPC instead of proving a port is open |
| `phoenix` | `GET /healthz` | Phoenix's own endpoint |
| `litellm` | `GET /health/readiness` | `/health` sits behind `user_api_key_auth` in 1.94.0 and would need a virtual key |
| `worker` | settings load | Cheap liveness for a process with no server |

## Running without containers

Where container images cannot be pulled, `make up-local` starts Phoenix and
LiteLLM as local processes at the **same pinned versions**, each in its own
virtualenv:

```bash
uv venv --python 3.12 .venv-phoenix
uv pip install --python .venv-phoenix/bin/python arize-phoenix==19.10.0
uv venv --python 3.12 .venv-litellm
uv pip install --python .venv-litellm/bin/python 'litellm[proxy]==1.94.0'
make up-local
```

This **cannot** start Temporal — the dev server is a downloaded binary, not a pip
package. Without it, runs take the degraded local executor and are stamped
`NON_DURABLE_EXECUTION` (ADR-0006). Those runs demonstrate the investigation, the
gates and the decision; they demonstrate nothing about durability.

## Troubleshooting

**`container rws-temporal is unhealthy` within ~30 seconds.**
Too fast to have exhausted the retry budget, so the process exited rather than
being slow. Check `docker compose logs temporal` — this happened once with an
invalid flag combination (`--ui-ip` alongside `--ip`, and `--namespace=default`
when `start-dev` already creates it). Both were removed; see the comment on the
service in `docker-compose.yml`.

**`make health` reports 2/4 healthy with Temporal down.**
Expected when running via `make up-local`. The message says so and names the
consequence.

**LiteLLM health check returns 401.**
You are hitting `/health` instead of `/health/readiness`.

**A run reports `infrastructure_failure` with `missing_mandatory_trace`.**
Phoenix did not receive the spans. This blocks acceptance and says **nothing**
about the patch (ADR-0012). Check that `PHOENIX_ENDPOINT` is set and reachable.

**Evaluations behave differently on the host and in the container.**
They should not. If an activity fails on a path that exists on one and not the
other, check that the inline worker is using its run-scoped task queue
(ADR-0013).

## Environment

Copy `.env.example` to `.env`. The defaults work as-is; `.env` is gitignored and
must never be committed. Provider keys are only needed for the optional live path,
which this task does not use.
