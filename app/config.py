"""Environment-driven configuration.

Read once, at process start, into a frozen object. Nothing else in the application
reads ``os.environ`` — a setting that can change mid-run is a setting that will
disagree with the artifacts describing the run.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_ROOT = REPOSITORY_ROOT / "fixtures" / "duplicate-job-processing"


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Everything the application needs from its environment."""

    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "reliability-walking-skeleton"

    litellm_base_url: str = "http://localhost:4000"
    litellm_master_key: str = "sk-local-mock-only"

    phoenix_endpoint: str | None = None
    phoenix_project_name: str = "reliability-walking-skeleton"

    #: "temporal" | "local" | "auto"
    execution_mode: str = "auto"
    var_dir: Path = REPOSITORY_ROOT / "var"
    inspect_sandbox: str = "local"
    enable_live_providers: bool = False

    @classmethod
    def from_environment(cls) -> Settings:
        var_dir = Path(os.environ.get("VAR_DIR", str(REPOSITORY_ROOT / "var"))).resolve()
        return cls(
            temporal_address=os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
            temporal_namespace=os.environ.get("TEMPORAL_NAMESPACE", "default"),
            temporal_task_queue=os.environ.get(
                "TEMPORAL_TASK_QUEUE", "reliability-walking-skeleton"
            ),
            litellm_base_url=os.environ.get("LITELLM_BASE_URL", "http://localhost:4000"),
            litellm_master_key=os.environ.get("LITELLM_MASTER_KEY", "sk-local-mock-only"),
            phoenix_endpoint=os.environ.get("PHOENIX_ENDPOINT") or None,
            phoenix_project_name=os.environ.get(
                "PHOENIX_PROJECT_NAME", "reliability-walking-skeleton"
            ),
            execution_mode=os.environ.get("EXECUTION_MODE", "auto"),
            var_dir=var_dir,
            inspect_sandbox=os.environ.get("INSPECT_SANDBOX", "local"),
            enable_live_providers=_flag("ENABLE_LIVE_PROVIDERS"),
        )

    # -- derived paths ----------------------------------------------------

    @property
    def audit_database(self) -> Path:
        """Agent-accessible store. Contains pseudonyms only."""
        return self.var_dir / "audit.db"

    @property
    def privileged_database(self) -> Path:
        """Privileged store. Real vendor/model mappings (ADR-0008)."""
        return self.var_dir / "privileged.db"

    @property
    def working_copies(self) -> Path:
        return self.var_dir / "working-copies"

    def ensure_directories(self) -> None:
        self.var_dir.mkdir(parents=True, exist_ok=True)
        self.working_copies.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    return Settings.from_environment()
