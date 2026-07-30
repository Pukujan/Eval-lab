# Developer commands for the reliability walking skeleton.
#
# Every target below works without paid API credentials. `make test`, `make eval`
# and `make demo` additionally work with no running services at all — they fall
# back to in-process LiteLLM dispatch and the degraded local executor, and label
# the result NON_DURABLE_EXECUTION (ADR-0006, ADR-0011).

SHELL := /bin/bash
VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
COMPOSE := docker compose

export PROMPTFOO_PYTHON := $(abspath $(PY))
export PROMPTFOO_DISABLE_TELEMETRY := 1
export PROMPTFOO_DISABLE_UPDATE := 1

.PHONY: setup up up-local health test eval eval-inspect eval-promptfoo demo traces down clean \
        lint format typecheck security ci-local help

help:
	@echo "setup   install pinned dependencies into $(VENV)"
	@echo "up      start Temporal, Phoenix and LiteLLM (Docker Compose)"
	@echo "up-local  start Phoenix and LiteLLM as local processes (no containers)"
	@echo "health  verify every service"
	@echo "test    deterministic tests, mock models, no credentials"
	@echo "eval    Inspect AI + Promptfoo evaluations"
	@echo "demo    the complete walking-skeleton scenario"
	@echo "traces  print the Phoenix URL and recent trace identifiers"
	@echo "down    stop services"
	@echo "clean   remove generated state and caches"

setup:
	python3.12 -m venv $(VENV) 2>/dev/null || python3 -m venv $(VENV)
	$(PIP) install --upgrade pip==25.3
	$(PIP) install -e ".[dev]"
	@echo
	@echo "Node tooling (pinned):  npm install -g promptfoo@0.121.19"
	@echo "Copy .env.example to .env if you want to change any defaults."

up:
	$(COMPOSE) up -d --wait
	@$(MAKE) --no-print-directory health

# Fallback for environments where container images cannot be pulled. Runs the
# SAME pinned versions of Phoenix and LiteLLM as local processes in their own
# virtualenvs. It cannot start Temporal (the dev server is a downloaded binary,
# not a pip package), so runs stay on the degraded local executor (ADR-0006).
up-local:
	bash scripts/serve_local_services.sh

health:
	@$(PY) scripts/health.py

test:
	$(PYTEST) tests -q

lint:
	$(VENV)/bin/ruff check app evals scripts tests
	$(VENV)/bin/ruff format --check app evals scripts tests

format:
	$(VENV)/bin/ruff format app evals scripts tests
	$(VENV)/bin/ruff check --fix app evals scripts tests

typecheck:
	$(VENV)/bin/mypy app

security:
	$(VENV)/bin/bandit -q -r app -c pyproject.toml

eval: eval-inspect eval-promptfoo

eval-inspect:
	@mkdir -p evals/logs
	$(VENV)/bin/inspect eval evals/inspect/coding_eval.py \
		--model mockllm/model --log-dir evals/logs --display plain

eval-promptfoo:
	@mkdir -p evals/reports
	cd evals/promptfoo && promptfoo eval -c promptfooconfig.yaml --no-cache \
		-o ../reports/promptfoo-report.json

demo:
	$(PY) scripts/demo.py

traces:
	@$(PY) scripts/traces.py

down:
	$(COMPOSE) down

clean:
	$(COMPOSE) down -v 2>/dev/null || true
	rm -rf var evals/logs evals/reports .pytest_cache .mypy_cache .ruff_cache .hypothesis
	find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true

# What CI runs, in order.
ci-local: lint typecheck security test eval
