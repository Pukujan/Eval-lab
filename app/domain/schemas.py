"""Runtime-validated, versioned domain schemas.

One schema-validation library (Pydantic v2 — ADR-0003), one convention:

* every model carries an explicit ``schema_version`` in the *payload*, not just in
  the file, so a persisted record can be identified years later;
* ``extra="forbid"`` — a record that invents a field is an error, because evidence
  that silently absorbs junk is not evidence;
* ``frozen=True`` and **tuples** for sequences. Pydantic's ``frozen`` is shallow, so
  a frozen model holding a ``list`` is not actually immutable.

These models are the vocabulary of the lab. No pinned platform defines
``RootCauseHypothesis`` or ``FalsificationProbe`` — that is why they are custom
(see docs/build-vs-integrate.md).
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

SCHEMA_VERSION = 1


class _Base(BaseModel):
    """Shared configuration for every domain schema."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1

    def content_hash(self) -> str:
        """Stable sha256 over the canonical JSON form.

        Used to content-address evidence so a record cannot be edited without the
        change being visible (threat model T-7).
        """
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class InvariantKind(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"


class EvidencePolarity(StrEnum):
    """Evidence is kept whether or not it helped. Contradicting evidence that is
    quietly dropped is the single most common way a wrong diagnosis survives."""

    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    NEUTRAL = "neutral"


class ProbeOutcome(StrEnum):
    SUPPORTED = "supported"
    FALSIFIED = "falsified"
    INCONCLUSIVE = "inconclusive"


class RepairStrategy(StrEnum):
    """How a candidate claims to fix the problem.

    ``SYMPTOM_SUPPRESSION`` exists so a candidate can be *labelled* honestly, but
    the label is never trusted: the gate decides from the effect counter, not from
    what the candidate calls itself (ADR-0009).
    """

    ESTABLISH_INVARIANT = "establish_invariant"
    SERIALISE_ACCESS = "serialise_access"
    IDEMPOTENT_EFFECT = "idempotent_effect"
    SYMPTOM_SUPPRESSION = "symptom_suppression"


class ExecutionMode(StrEnum):
    TEMPORAL = "temporal"
    LOCAL = "local"


class ModelRole(StrEnum):
    SOLVER = "solver"
    CRITIC = "critic"
    VERIFIER = "verifier"
    COMPARISON = "comparison"


# ---------------------------------------------------------------------------
# Problem definition
# ---------------------------------------------------------------------------


class SystemInvariant(_Base):
    """A property the repository under test must maintain."""

    invariant_id: str
    statement: str
    kind: InvariantKind = InvariantKind.SECONDARY
    #: Dotted path or file reference to the deterministic check that decides it.
    check_reference: str


class ProblemSpecification(_Base):
    """The structured bug report plus what the system is supposed to do."""

    specification_id: str
    title: str
    reported_symptom: str
    repository_path: str
    expected_behaviour: str
    invariants: tuple[SystemInvariant, ...] = ()
    #: Paths a patch may never touch (tests, the reference answer, CI config).
    prohibited_paths: tuple[str, ...] = ()

    @field_validator("invariants")
    @classmethod
    def _exactly_one_primary(
        cls, value: tuple[SystemInvariant, ...]
    ) -> tuple[SystemInvariant, ...]:
        primaries = [i for i in value if i.kind is InvariantKind.PRIMARY]
        if value and len(primaries) != 1:
            raise ValueError(
                f"a specification needs exactly one primary invariant, found {len(primaries)}"
            )
        return value

    @property
    def primary_invariant(self) -> SystemInvariant | None:
        return next((i for i in self.invariants if i.kind is InvariantKind.PRIMARY), None)


# ---------------------------------------------------------------------------
# Investigation
# ---------------------------------------------------------------------------


class Assumption(_Base):
    """Something a hypothesis needs to be true, stated so it can be attacked."""

    assumption_id: str
    statement: str
    #: False means the assumption cannot be checked by any probe we can build —
    #: which is itself a reason to distrust the hypothesis resting on it.
    falsifiable: bool = True


class Evidence(_Base):
    """One observation, retained regardless of which way it points."""

    evidence_id: str
    source: str
    polarity: EvidencePolarity
    summary: str
    #: Hash of the underlying artifact, so the record is verifiable without
    #: storing (possibly sensitive) raw output.
    payload_sha256: str
    artifact_reference: str | None = None

    @field_validator("payload_sha256")
    @classmethod
    def _looks_like_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("payload_sha256 must be a lowercase hex sha256 digest")
        return value


class RootCauseHypothesis(_Base):
    """A causal story with a stated way to prove it wrong.

    Every field below is required precisely because the failure mode this lab
    studies is a plausible-sounding cause with no falsification condition.
    """

    hypothesis_id: str
    causal_mechanism: str
    #: Coarse class of mechanism. Two hypotheses sharing a class are not causally
    #: distinct, which is how the "at least three distinct hypotheses" requirement
    #: is actually checked rather than merely counted.
    mechanism_class: str
    assumptions: tuple[Assumption, ...]
    predicted_observations: tuple[str, ...]
    falsification_condition: str
    proposed_probe_id: str

    @field_validator("assumptions", "predicted_observations")
    @classmethod
    def _non_empty(cls, value: tuple[Any, ...]) -> tuple[Any, ...]:
        if not value:
            raise ValueError("a hypothesis needs at least one assumption and prediction")
        return value


class FalsificationProbe(_Base):
    """A deterministic experiment that discriminates between hypotheses."""

    probe_id: str
    hypothesis_id: str
    description: str
    #: Dotted path of the probe implementation. Probes are code, not prose.
    implementation: str
    deterministic: bool = True
    #: Hypothesis ids this probe is expected to tell apart.
    discriminates: tuple[str, ...] = ()


class ProbeResult(_Base):
    """What running a probe actually showed."""

    probe_id: str
    hypothesis_id: str
    outcome: ProbeOutcome
    observations: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    exit_code: int | None = None


# ---------------------------------------------------------------------------
# Repair
# ---------------------------------------------------------------------------


class FileChange(_Base):
    """A single file rewrite. Whole-file content keeps application deterministic —
    no fuzzy patch application, no context-matching ambiguity."""

    path: str
    new_content: str


class PatchArtifact(_Base):
    """The concrete change a candidate proposes."""

    patch_id: str
    candidate_id: str
    changes: tuple[FileChange, ...]
    #: Provenance label, e.g. "reference" or "duct-tape". Never used by a gate;
    #: gates read behaviour, not labels.
    source_label: str = "generated"

    @property
    def touched_paths(self) -> tuple[str, ...]:
        return tuple(change.path for change in self.changes)


class RepairCandidate(_Base):
    """A proposed fix, tied to the hypothesis it claims to address."""

    candidate_id: str
    hypothesis_id: str
    strategy: RepairStrategy
    description: str
    patch_id: str
    #: The candidate's own claim about whether it addresses the causal mechanism.
    #: Treated as a claim to be tested, never as a finding.
    claims_mechanism_addressed: bool


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


class VerificationResult(_Base):
    """Observable outcomes of building and testing a patched working copy.

    Every field is a fact a machine read off a process: an exit code, a count, a
    path set. Nothing here is a judgement.
    """

    candidate_id: str
    patch_id: str
    build_succeeded: bool
    visible_tests_passed: bool
    #: Per-test node ids that passed before and after the patch. Regression is a
    #: set difference over these, not a suite-level boolean — a patch that fixes
    #: one test while breaking another must not look like an improvement.
    visible_tests_passing_before: tuple[str, ...] = ()
    visible_tests_passing_after: tuple[str, ...] = ()
    hidden_tests_passed: bool = False
    property_tests_passed: bool
    invariant_holds: bool
    #: Times the fixture's external effect actually executed for one logical job
    #: id. This is what separates a real fix (1) from duct tape (2) — the output
    #: log can be deduplicated, but the effect counter cannot be talked down.
    effect_invocation_count: int
    committed_result_count: int
    prohibited_paths_touched: tuple[str, ...] = ()
    build_output_sha256: str | None = None
    duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------


class GateResult(_Base):
    """One reliability gate's verdict."""

    gate_name: str
    passed: bool
    #: Why, in terms of the artifact the gate read.
    detail: str


class ReliabilityDecision(_Base):
    """The terminal outcome, with the gate evidence that produced it."""

    run_id: str
    #: Constrained to the four terminal states. "approved"/"correct"/"safe"/
    #: "production_ready" are not expressible here by construction.
    outcome: Literal["accepted_for_review", "rejected", "abstained", "infrastructure_failure"]
    gate_results: tuple[GateResult, ...]
    rationale: str
    caveats: tuple[str, ...] = ()
    #: False whenever the run used the degraded local executor (ADR-0006).
    durable_execution: bool = True

    @field_validator("gate_results")
    @classmethod
    def _decision_needs_gates(cls, value: tuple[GateResult, ...]) -> tuple[GateResult, ...]:
        if not value:
            raise ValueError("a reliability decision must cite at least one gate result")
        return value

    @property
    def failed_gates(self) -> tuple[str, ...]:
        return tuple(g.gate_name for g in self.gate_results if not g.passed)


# ---------------------------------------------------------------------------
# Model identity
# ---------------------------------------------------------------------------


class AnonymousModelIdentity(_Base):
    """What solver, critic, verifier and comparison roles are allowed to see.

    Contains no vendor, no real model id, and nothing correlatable across runs.
    """

    pseudonym: str
    role: ModelRole
    #: Position after per-run shuffling; carries no information about identity.
    presentation_order: int

    @field_validator("pseudonym")
    @classmethod
    def _pseudonym_shape(cls, value: str) -> str:
        if not value.startswith("model-") or len(value) != len("model-") + 8:
            raise ValueError("pseudonym must look like 'model-<8 hex chars>'")
        return value


class PrivilegedModelIdentity(_Base):
    """The real mapping. Lives only in ``var/privileged.db`` (ADR-0008).

    This model must never be embedded in a prompt, a span attribute, a report, or
    anything reachable from :mod:`app.storage.audit`.
    """

    pseudonym: str
    vendor: str
    model_identifier: str
    #: What the gateway actually resolved, read back from the response rather than
    #: assumed from the alias.
    resolved_model_identifier: str
    endpoint: str


# ---------------------------------------------------------------------------
# Run records
# ---------------------------------------------------------------------------


class EvaluationRun(_Base):
    """One end-to-end execution of the walking skeleton."""

    run_id: str
    specification_id: str
    execution_mode: ExecutionMode
    #: Seeds the per-run candidate shuffle: reproducible given the run id,
    #: unpredictable across runs.
    run_seed: int
    started_at: str
    finished_at: str | None = None
    anonymous_identities: tuple[AnonymousModelIdentity, ...] = ()
    trace_id: str | None = None
    workflow_id: str | None = None


class ReleaseManifest(_Base):
    """Everything needed to say what produced a given result.

    A reliability claim without the exact versions that produced it is not
    reproducible, which is why this is a first-class schema rather than a log line.
    """

    manifest_id: str
    run_id: str
    #: package/image name -> exact version or digest.
    component_versions: tuple[tuple[str, str], ...]
    fixture_revision: str
    decision_outcome: Literal[
        "accepted_for_review", "rejected", "abstained", "infrastructure_failure"
    ]
    artifact_paths: tuple[str, ...] = ()
    #: Set when anything about the run weakens the claim (e.g. non-durable
    #: execution, or a service that was unreachable).
    caveats: tuple[str, ...] = ()


#: Every domain schema, used by the schema-export script and by Promptfoo's
#: deterministic JSON-schema assertions — one definition, two consumers.
ALL_SCHEMAS: tuple[type[_Base], ...] = (
    ProblemSpecification,
    SystemInvariant,
    RootCauseHypothesis,
    Assumption,
    Evidence,
    FalsificationProbe,
    ProbeResult,
    RepairCandidate,
    PatchArtifact,
    VerificationResult,
    ReliabilityDecision,
    EvaluationRun,
    AnonymousModelIdentity,
    PrivilegedModelIdentity,
    ReleaseManifest,
)
