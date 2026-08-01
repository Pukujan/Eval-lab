"""The Task 2B run plan: an explicit, human-selected, validated model set.

Task 2B is the first time this lab would send a prompt to a model it did not
write. That changes what an error costs. In Task 2A a misconfiguration produced a
red build; here it can produce a *green* build carrying evidence about a model
that was never actually asked. So the plan is a separate, inspectable object with
three properties that the rest of the harness depends on.

**The evaluation set comes from a frozen snapshot, never from code.** An earlier
version of this module carried eleven aliases "observed on the gateway" plus a
flag to opt into anything outside them. Both are gone. The list in code went stale
the moment the gateway grew, described *production* rather than the evaluation
service, and — worst — read as authoritative. The opt-in flag was worse still: it
turned "this alias is not in the frozen set" from a hard stop into a box someone
ticks. A benchmark run now requires :mod:`app.models.alias_snapshot`, and the only
thing that decides which aliases are evaluated is that hashed artifact.

**The connectivity canary is not the benchmark.** One ``gpt-5.6-luna`` request
proving the endpoint answers is a different kind of run from a frozen frontier
campaign, and conflating them is how a smoke test ends up cited as evidence. They
are separate :class:`RunKind` values: the canary needs no snapshot and its
evidence is stamped as non-benchmark; the benchmark cannot start without one.

**Aliases are opaque strings.** Several confirmed ones contain spaces and square
brackets (``[aws]glm-5``, ``[grok] grok-4.5``). They are never split, globbed,
lower-cased, or handed to a shell, and any path derived from one goes through
:func:`alias_slug`, which is a hash with a readable prefix rather than the alias
itself.

**Execution is blocked, and the block lives in code.** :data:`EXECUTION_BLOCKED`
is checked immediately before egress, not only in documentation or in CI, because
a scaffold whose only guard is a paragraph in a markdown file is one careless
``python -m`` away from making a live request.

Nothing here claims the plan is calibrated or that any limit is a good limit. The
defaults are conservative bounds chosen so that an unattended mistake is small;
the only prior art in this repository is ``DEFAULT_TIMEOUT_SECONDS = 30.0`` in
``app/models/gateway.py`` and the 120-second bound in the CKFF smoke action.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for runtime
    from app.models.alias_snapshot import FrozenAliasSnapshot

# ---------------------------------------------------------------------------
# Blocked state
# ---------------------------------------------------------------------------

#: While true, no code path in this package may contact the gateway. Flipping it
#: is a deliberate act that should accompany evidence that both preconditions
#: below actually hold — it is not a convenience switch.
EXECUTION_BLOCKED: Final[bool] = True

#: What has to be true before Task 2B may execute. Stated as prose rather than as
#: flags because neither condition is machine-checkable from inside this
#: repository, and pretending otherwise would be a fake gate.
BLOCKING_PRECONDITIONS: Final[tuple[str, ...]] = (
    "a current sanitized validator artifact from the evaluation service is on record, "
    "with its timestamp and the deployment identifier it describes",
    "that artifact shows the __canary_invalid route FAILED FAST rather than returning "
    "200; a 200 means something silently fell back and no number from the service is "
    "attributable",
    "the five documented hidden-retry sources are each closed on the evaluation "
    "service: litellm_settings.num_retries, router_settings.num_retries, multi-route "
    "pooling of an alias, cooldowns parking a failing route, and client SDK defaults",
    "drop_params is false, so a parameter the harness believes it sent was actually sent",
    "a frozen ordered alias snapshot exists for the evaluation service, hashed, with "
    "its retrieval timestamp, source, method and deployment identifier",
)

#: The account-wide ckff limit is 100 requests per minute, counted across every
#: model. Pacing is the harness's job: the evaluation service deliberately has no
#: request queue, because queueing would hide a 429 that is itself evidence.
ACCOUNT_REQUESTS_PER_MINUTE: Final[int] = 100

#: Headroom below the account limit. A self-inflicted 429 is indistinguishable
#: from a genuine one in the record, so the harness stays well under.
DEFAULT_REQUESTS_PER_MINUTE: Final[int] = 30

#: Tool-calling below this token ceiling produces false negatives: reasoning
#: models emit reasoning content before the tool call and truncate before it
#: appears. Recorded here so no future caller rediscovers it the expensive way.
MIN_TOOL_CALL_MAX_TOKENS: Final[int] = 256


class ExecutionBlockedError(RuntimeError):
    """Raised when something tries to contact the gateway while Task 2B is blocked."""


class PlanError(ValueError):
    """Raised when a run plan is not one this harness will accept."""


def assert_execution_allowed() -> None:
    """Refuse to proceed while Task 2B is blocked.

    Called immediately before egress rather than at import time so that the
    offline parts of this package — validation, planning, evidence shaping —
    remain testable without weakening the guard.
    """
    if EXECUTION_BLOCKED:
        reasons = "; ".join(BLOCKING_PRECONDITIONS)
        raise ExecutionBlockedError(
            "Task 2B execution is blocked. Unmet preconditions: "
            f"{reasons}. No gateway request was made."
        )


# ---------------------------------------------------------------------------
# Aliases
# ---------------------------------------------------------------------------


class RunKind(StrEnum):
    """What a run is for. The two are never the same evidence.

    ``CONNECTIVITY_CANARY`` is one request to one alias, asking only whether the
    endpoint answers at all. It precedes the freeze, so it cannot require a
    snapshot — and precisely because it cannot, its evidence is stamped as
    non-benchmark so it can never be cited as a model result.

    ``FRONTIER_BENCHMARK`` is the campaign. It refuses to exist without a frozen,
    hashed snapshot of the evaluation service's aliases.
    """

    CONNECTIVITY_CANARY = "connectivity_canary"
    FRONTIER_BENCHMARK = "frontier_benchmark"


#: The single alias the connectivity canary may use. Named rather than free so a
#: "canary" cannot quietly become a one-model benchmark of something else.
CANARY_ALIAS: Final[str] = "gpt-5.6-luna"

#: Characters an alias may contain. Deliberately an allowlist: spaces and square
#: brackets have to be permitted because real aliases use them, so a denylist of
#: "dangerous" characters would have to permit the glob characters anyway and
#: would give false comfort. Safety comes from never passing an alias to a shell,
#: not from the character set.
_ALIAS_CHARACTERS: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9 ._:/\[\]-]+$")

MAX_ALIAS_LENGTH: Final[int] = 128


def validate_alias(alias: object) -> str:
    """Return ``alias`` unchanged, or raise :class:`PlanError`.

    Unchanged is the point. The alias is compared byte-for-byte against the
    ``model`` field the gateway echoes back, so normalising it here — trimming,
    case-folding, collapsing spaces — would quietly convert a substitution into a
    match. Padding is rejected rather than stripped for the same reason.
    """
    if not isinstance(alias, str):
        raise PlanError(f"model alias must be a string, got {type(alias).__name__}")
    if not alias:
        raise PlanError("model alias is empty")
    if alias != alias.strip():
        raise PlanError(
            f"model alias {alias!r} has leading or trailing whitespace; it is used for an "
            "exact comparison against the gateway's response and is never trimmed"
        )
    if len(alias) > MAX_ALIAS_LENGTH:
        raise PlanError(f"model alias is longer than {MAX_ALIAS_LENGTH} characters")
    if not alias.isascii():
        raise PlanError(
            f"model alias {alias!r} contains non-ASCII characters; a homoglyph would "
            "read as the intended alias while naming a different model"
        )
    if not _ALIAS_CHARACTERS.match(alias):
        raise PlanError(
            f"model alias {alias!r} contains characters outside the permitted set "
            "(letters, digits, space, and . _ : / - [ ])"
        )
    return alias


def alias_slug(alias: str) -> str:
    """A filesystem-safe identity for an alias, for evidence filenames.

    The readable prefix is a convenience; the 12 hex characters are what makes it
    unique. ``[aws]glm-5`` and ``aws-glm-5`` collapse to the same prefix and are
    kept apart by the digest, so one model's evidence can never land on another's
    path.
    """
    validate_alias(alias)
    digest = hashlib.sha256(alias.encode("utf-8")).hexdigest()[:12]
    readable = re.sub(r"[^a-z0-9]+", "-", alias.lower()).strip("-") or "alias"
    return f"{readable[:48]}-{digest}"


# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------

# Ceilings, not recommendations. A caller may configure anything up to these; the
# point of the ceiling is that a mistyped dispatch input cannot turn a bounded
# preflight into an unbounded spend.
MAX_REQUEST_TIMEOUT_SECONDS: Final[float] = 120.0
MAX_TOTAL_WALL_CLOCK_SECONDS: Final[float] = 3600.0
MAX_REQUESTS_PER_MODEL_CEILING: Final[int] = 20
MAX_TOTAL_REQUESTS_CEILING: Final[int] = 200
MAX_COMPLETION_TOKENS_CEILING: Final[int] = 4096
MAX_RESPONSE_BYTES_CEILING: Final[int] = 1_048_576
MAX_CONTENT_CHARACTERS_CEILING: Final[int] = 65_536


@dataclass(frozen=True)
class RunLimits:
    """Every bound a run is subject to, in one place.

    Defaults are deliberately small. One request per model is the honest starting
    shape for a connectivity-and-attribution exercise: until the zero-retry route
    is confirmed, more requests only produce more unattributable numbers.
    """

    request_timeout_seconds: float = 60.0
    total_wall_clock_seconds: float = 900.0
    max_requests_per_model: int = 1
    max_completion_tokens: int = 512
    max_response_bytes: int = 262_144
    max_content_characters: int = 16_384

    def __post_init__(self) -> None:
        self._require_positive("request_timeout_seconds", self.request_timeout_seconds)
        self._require_positive("total_wall_clock_seconds", self.total_wall_clock_seconds)
        self._require_positive("max_requests_per_model", self.max_requests_per_model)
        self._require_positive("max_completion_tokens", self.max_completion_tokens)
        self._require_positive("max_response_bytes", self.max_response_bytes)
        self._require_positive("max_content_characters", self.max_content_characters)

        self._require_at_most(
            "request_timeout_seconds", self.request_timeout_seconds, MAX_REQUEST_TIMEOUT_SECONDS
        )
        self._require_at_most(
            "total_wall_clock_seconds", self.total_wall_clock_seconds, MAX_TOTAL_WALL_CLOCK_SECONDS
        )
        self._require_at_most(
            "max_requests_per_model", self.max_requests_per_model, MAX_REQUESTS_PER_MODEL_CEILING
        )
        self._require_at_most(
            "max_completion_tokens", self.max_completion_tokens, MAX_COMPLETION_TOKENS_CEILING
        )
        self._require_at_most(
            "max_response_bytes", self.max_response_bytes, MAX_RESPONSE_BYTES_CEILING
        )
        self._require_at_most(
            "max_content_characters",
            self.max_content_characters,
            MAX_CONTENT_CHARACTERS_CEILING,
        )

        if self.request_timeout_seconds > self.total_wall_clock_seconds:
            raise PlanError(
                "request_timeout_seconds exceeds total_wall_clock_seconds; the run bound "
                "would never be reached and the per-request bound would be the only one"
            )

    @staticmethod
    def _require_positive(name: str, value: float) -> None:
        if not isinstance(value, int | float) or isinstance(value, bool):
            raise PlanError(f"{name} must be a number")
        if value <= 0:
            raise PlanError(f"{name} must be greater than zero, got {value!r}")

    @staticmethod
    def _require_at_most(name: str, value: float, ceiling: float) -> None:
        if value > ceiling:
            raise PlanError(f"{name}={value!r} exceeds the hard ceiling of {ceiling!r}")

    def as_document(self) -> dict[str, Any]:
        return {
            "request_timeout_seconds": self.request_timeout_seconds,
            "total_wall_clock_seconds": self.total_wall_clock_seconds,
            "max_requests_per_model": self.max_requests_per_model,
            "max_completion_tokens": self.max_completion_tokens,
            "max_response_bytes": self.max_response_bytes,
            "max_content_characters": self.max_content_characters,
        }


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PromptSpec:
    """One fixed prompt, identified by id.

    Free-form prompt text is not accepted anywhere in this package. That is the
    mechanism behind "no secrets and no private verifier material in prompts":
    the only strings that can reach the gateway are the ones written here, in the
    open, reviewable in a diff. A prompt assembled at runtime from a dispatch
    input or an environment variable is exactly how a key or a holdout ends up in
    someone else's log file.
    """

    prompt_id: str
    system: str
    user: str


DEFAULT_PROMPT_ID: Final[str] = "task-2b-preflight-v1"

PROMPT_CATALOGUE: Final[dict[str, PromptSpec]] = {
    DEFAULT_PROMPT_ID: PromptSpec(
        prompt_id=DEFAULT_PROMPT_ID,
        system="Answer with a single word and nothing else.",
        user="Reply with the word OK.",
    ),
}


def get_prompt(prompt_id: str) -> PromptSpec:
    try:
        return PROMPT_CATALOGUE[prompt_id]
    except KeyError as exc:
        raise PlanError(
            f"prompt id {prompt_id!r} is not in the catalogue; known ids: "
            f"{sorted(PROMPT_CATALOGUE)}. Free-form prompt text is not accepted."
        ) from exc


# ---------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SequentialRunPlan:
    """What a Task 2B run would do, fully specified before anything is contacted."""

    model_aliases: tuple[str, ...]
    limits: RunLimits = field(default_factory=RunLimits)
    prompt_id: str = DEFAULT_PROMPT_ID
    #: Free text naming who chose this set and where they wrote it down.
    selection_source: str = "unspecified"
    run_kind: RunKind = RunKind.FRONTIER_BENCHMARK
    #: The frozen snapshot this benchmark evaluates. Required for a benchmark;
    #: absent for the canary, which runs before any freeze exists.
    snapshot: FrozenAliasSnapshot | None = None
    #: Requests per minute this run may issue, account-wide across all models.
    requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE

    def __post_init__(self) -> None:
        if not isinstance(self.model_aliases, tuple):
            raise PlanError("model_aliases must be a tuple")
        if not self.model_aliases:
            raise PlanError(
                "no model was selected. The Task 2B evaluation set is deliberately "
                "unchosen; a human must name the aliases explicitly."
            )
        for alias in self.model_aliases:
            validate_alias(alias)
        duplicates = sorted({a for a in self.model_aliases if self.model_aliases.count(a) > 1})
        if duplicates:
            raise PlanError(
                f"model set contains duplicates {duplicates}; evidence is written per "
                "alias and a repeated alias would blend two runs into one record"
            )
        get_prompt(self.prompt_id)
        if self.total_request_budget > MAX_TOTAL_REQUESTS_CEILING:
            raise PlanError(
                f"{len(self.model_aliases)} models x {self.limits.max_requests_per_model} "
                f"requests = {self.total_request_budget}, above the hard ceiling of "
                f"{MAX_TOTAL_REQUESTS_CEILING}"
            )
        if not 1 <= self.requests_per_minute <= ACCOUNT_REQUESTS_PER_MINUTE:
            raise PlanError(
                f"requests_per_minute must be between 1 and {ACCOUNT_REQUESTS_PER_MINUTE} "
                f"(the account-wide ckff limit), got {self.requests_per_minute}. Exceeding "
                "it produces self-inflicted 429s that are indistinguishable in the record "
                "from a model genuinely failing."
            )

        if self.run_kind is RunKind.CONNECTIVITY_CANARY:
            if self.model_aliases != (CANARY_ALIAS,):
                raise PlanError(
                    f"a connectivity canary runs exactly one alias, {CANARY_ALIAS!r}; got "
                    f"{list(self.model_aliases)}. Anything wider is a benchmark and needs "
                    "a frozen snapshot."
                )
            if self.snapshot is not None:
                raise PlanError(
                    "a connectivity canary must not carry a frozen snapshot; it runs "
                    "before the freeze and its evidence is not benchmark evidence"
                )
            return

        # Benchmark. The snapshot is the authority, and the plan may not differ
        # from it in content or in order.
        if self.snapshot is None:
            raise PlanError(
                "a frontier benchmark requires a frozen alias snapshot of the evaluation "
                "service. There is no opt-out: an ad-hoc list cannot be tied to a "
                "retrieval time, a source, or a deployment, so nothing it produces is "
                "attributable. Freeze the list first."
            )
        if self.model_aliases != self.snapshot.aliases:
            raise PlanError(
                "the model set does not match the frozen snapshot exactly. Adding, "
                "removing, renaming, substituting or reordering an alias after the freeze "
                "makes this a different campaign, which needs a new snapshot rather than "
                "a mutated one.\n"
                f"  snapshot: {list(self.snapshot.aliases)}\n"
                f"  plan    : {list(self.model_aliases)}"
            )

    @property
    def total_request_budget(self) -> int:
        return len(self.model_aliases) * self.limits.max_requests_per_model

    def as_document(self) -> dict[str, Any]:
        """The run-plan artifact.

        Records what would be asked and under which bounds. It asserts nothing
        about any model, and it deliberately carries no credential, no base URL
        chosen at runtime, and no prompt text beyond its catalogue id.
        """
        return {
            "document_kind": "task_2b_sequential_run_plan",
            "asserts": (
                "Nothing about any model. This records which aliases a human "
                "selected, under which bounds, and that execution remains blocked."
            ),
            "execution_blocked": EXECUTION_BLOCKED,
            "blocking_preconditions": list(BLOCKING_PRECONDITIONS),
            "run_kind": str(self.run_kind),
            # The canary answers "does the endpoint reply". It is not a model
            # result and must never be quoted as one.
            "is_benchmark_evidence": self.run_kind is RunKind.FRONTIER_BENCHMARK,
            "model_aliases": list(self.model_aliases),
            "model_slugs": {alias: alias_slug(alias) for alias in self.model_aliases},
            "alias_snapshot": self.snapshot.as_document() if self.snapshot else None,
            "selection_source": self.selection_source,
            "prompt_id": self.prompt_id,
            "limits": self.limits.as_document(),
            "total_request_budget": self.total_request_budget,
            "requests_per_minute": self.requests_per_minute,
            "account_requests_per_minute": ACCOUNT_REQUESTS_PER_MINUTE,
            "min_tool_call_max_tokens": MIN_TOOL_CALL_MAX_TOKENS,
            "concurrency": 1,
            "client_retry_count": 0,
            "follow_redirects": False,
            "model_substitution_permitted": False,
            "cross_model_fallback_permitted": False,
            "retry_owner": "temporal",
        }


def parse_model_selection(raw: object) -> tuple[str, ...]:
    """Parse the human's model selection from a dispatch input.

    A JSON array is the only accepted form, and the reason is the aliases
    themselves: ``[aws]glm-5`` begins with a bracket and ``[ds2] deepseek-v4-pro``
    contains a space, so any delimiter-sniffing parser has to guess whether a
    leading ``[`` opens a list or names a model. Guessing here would select a
    different model than the operator intended, which is the one failure this
    whole module exists to prevent.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise PlanError(
            'no model set was provided. Pass a JSON array, for example ["gpt-5.6-luna"].'
        )
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        raise PlanError(
            f"model set is not valid JSON ({exc}). Pass a JSON array of exact aliases, "
            'for example ["gpt-5.6-luna", "[aws]glm-5"].'
        ) from exc
    if not isinstance(parsed, list):
        raise PlanError(f"model set must be a JSON array, got {type(parsed).__name__}")
    if not parsed:
        raise PlanError("model set is an empty array; a human must name at least one alias")
    return tuple(validate_alias(alias) for alias in parsed)


def build_benchmark_plan(
    snapshot: FrozenAliasSnapshot,
    *,
    limits: RunLimits | None = None,
    prompt_id: str = DEFAULT_PROMPT_ID,
    selection_source: str = "unspecified",
    requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
) -> SequentialRunPlan:
    """A benchmark plan, taking its aliases from the snapshot and nothing else.

    There is deliberately no parameter for the model set. Passing one would make
    the snapshot advisory, and the whole point of freezing is that the list is not
    a runtime decision.
    """
    return SequentialRunPlan(
        model_aliases=snapshot.aliases,
        limits=limits or RunLimits(),
        prompt_id=prompt_id,
        selection_source=selection_source,
        run_kind=RunKind.FRONTIER_BENCHMARK,
        snapshot=snapshot,
        requests_per_minute=requests_per_minute,
    )


def build_canary_plan(
    *,
    limits: RunLimits | None = None,
    prompt_id: str = DEFAULT_PROMPT_ID,
    selection_source: str = "connectivity canary",
) -> SequentialRunPlan:
    """One request to one alias, to learn only whether the endpoint answers."""
    canary_limits = limits or RunLimits(max_requests_per_model=1)
    return SequentialRunPlan(
        model_aliases=(CANARY_ALIAS,),
        limits=canary_limits,
        prompt_id=prompt_id,
        selection_source=selection_source,
        run_kind=RunKind.CONNECTIVITY_CANARY,
        snapshot=None,
        requests_per_minute=DEFAULT_REQUESTS_PER_MINUTE,
    )
