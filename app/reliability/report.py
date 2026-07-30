"""The structured reliability report.

Composes platform artifacts into the record a human reviewer actually needs. It
reports; it never decides — the decision arrives already made from
:mod:`app.reliability.gates`.

Vocabulary is enforced here as well as in the schema. The only positive outcome is
``accepted_for_review``, and the report says in as many words that acceptance means
"a human should look at this", not that anything is correct or safe.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import metadata
from typing import Any

from app.domain.schemas import (
    EvaluationRun,
    ReleaseManifest,
    ReliabilityDecision,
    VerificationResult,
)

#: Recorded on every manifest so a result can be tied to what produced it.
TRACKED_COMPONENTS = (
    "temporalio",
    "langgraph",
    "litellm",
    "inspect-ai",
    "pydantic",
    "opentelemetry-sdk",
    "arize-phoenix-otel",
    "hypothesis",
)

OUTCOME_MEANING = {
    "accepted_for_review": (
        "All deterministic reliability gates passed. A human reviewer should now "
        "examine this patch. This is NOT a claim that the patch is correct, safe, "
        "calibrated, or ready for production, and the patch has not been merged or "
        "deployed."
    ),
    "rejected": "At least one deterministic reliability gate failed.",
    "abstained": (
        "The system declined to judge: it could not establish a supported diagnosis. "
        "This is not a claim that the patch is wrong."
    ),
    "infrastructure_failure": ("The evaluation harness failed. This says nothing about the patch."),
}


def component_versions() -> tuple[tuple[str, str], ...]:
    """Installed versions of the components that produced a result."""
    versions: list[tuple[str, str]] = []
    for name in TRACKED_COMPONENTS:
        try:
            versions.append((name, metadata.version(name)))
        except metadata.PackageNotFoundError:
            versions.append((name, "not-installed"))
    return tuple(versions)


@dataclass(frozen=True)
class ReliabilityReport:
    """The structured report produced by a walking-skeleton run."""

    run: EvaluationRun
    decision: ReliabilityDecision
    verification: VerificationResult | None
    manifest: ReleaseManifest
    investigation: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run": self.run.model_dump(mode="json"),
            "decision": self.decision.model_dump(mode="json"),
            "outcome_meaning": OUTCOME_MEANING[self.decision.outcome],
            "verification": (
                self.verification.model_dump(mode="json") if self.verification else None
            ),
            "manifest": self.manifest.model_dump(mode="json"),
            "investigation": self.investigation,
            "merged_or_deployed": False,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def summary_lines(self) -> tuple[str, ...]:
        """Human-readable summary for `make demo`."""
        lines = [
            f"run              : {self.run.run_id}",
            f"execution mode   : {self.run.execution_mode}"
            + ("" if self.decision.durable_execution else "  (NON-DURABLE)"),
            f"outcome          : {self.decision.outcome.upper()}",
            f"rationale        : {self.decision.rationale}",
        ]
        if self.decision.gate_results:
            lines.append("gates:")
            for gate in self.decision.gate_results:
                mark = "PASS" if gate.passed else "FAIL"
                lines.append(f"  [{mark}] {gate.gate_name}: {gate.detail}")
        if self.decision.caveats:
            lines.append("caveats:")
            lines.extend(f"  - {caveat}" for caveat in self.decision.caveats)
        lines.append(f"meaning          : {OUTCOME_MEANING[self.decision.outcome]}")
        return tuple(lines)


def build_manifest(
    run: EvaluationRun,
    decision: ReliabilityDecision,
    *,
    fixture_revision: str,
    artifact_paths: tuple[str, ...] = (),
) -> ReleaseManifest:
    return ReleaseManifest(
        manifest_id=f"manifest-{run.run_id}",
        run_id=run.run_id,
        component_versions=component_versions(),
        fixture_revision=fixture_revision,
        decision_outcome=decision.outcome,
        artifact_paths=artifact_paths,
        caveats=decision.caveats,
    )
