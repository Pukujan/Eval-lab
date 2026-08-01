"""The Task 2B run plan: an explicit, human-selected, validated model set.

Task 2B is the first time this lab would send a prompt to a model it did not
write. That changes what an error costs. In Task 2A a misconfiguration produced a
red build; here it can produce a *green* build carrying evidence about a model
that was never actually asked. So the plan is a separate, inspectable object with
three properties that the rest of the harness depends on.

**The evaluation set is an input, not a constant.** The gateway exposes many
aliases and more keep appearing; which of them Task 2B evaluates is a research
decision nobody has taken yet. Hard-coding a list here would freeze an unmade
decision into code and make it look settled. :data:`OBSERVED_GATEWAY_ALIASES` is
therefore what has been *seen*, explicitly not what will be *run*, and a plan
cannot be constructed without a caller naming the models.

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
from typing import Any, Final

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
    "PR #1 is green and merged",
    "a confirmed CKFF route with zero hidden proxy retries exists for every alias "
    "under evaluation; the gateway's documented five same-model retries make any "
    "latency, failure, or cost figure unattributable",
)


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

#: Aliases observed on the CKFF gateway. **This is not the evaluation set.** It
#: exists so that a typo in a dispatch input is caught before a run rather than
#: after it, and it is expected to go stale as the gateway changes; an alias
#: outside this tuple is refused unless the caller opts in explicitly.
OBSERVED_GATEWAY_ALIASES: Final[tuple[str, ...]] = (
    "[aws]glm-5",
    "[aws]kimi-k2-thinking",
    "[aws]minimax-m2.5",
    "[ds2] deepseek-v4-pro",
    "[grok] grok-4.5",
    "claude-opus-4-7",
    "gemini-3.5-flash",
    "gpt-5.6-luna",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "qwen-3.6-max",
)

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
    #: Aliases not in :data:`OBSERVED_GATEWAY_ALIASES` that a caller opted into.
    unconfirmed_aliases: tuple[str, ...] = ()

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
        unknown = tuple(a for a in self.model_aliases if a not in OBSERVED_GATEWAY_ALIASES)
        if set(unknown) - set(self.unconfirmed_aliases):
            raise PlanError(
                f"aliases {sorted(set(unknown) - set(self.unconfirmed_aliases))} were not "
                "observed on the gateway. Re-check the spelling, or opt in explicitly if "
                "the gateway has genuinely changed."
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
            "model_aliases": list(self.model_aliases),
            "model_slugs": {alias: alias_slug(alias) for alias in self.model_aliases},
            "unconfirmed_aliases": list(self.unconfirmed_aliases),
            "selection_source": self.selection_source,
            "prompt_id": self.prompt_id,
            "limits": self.limits.as_document(),
            "total_request_budget": self.total_request_budget,
            "concurrency": 1,
            "client_retry_count": 0,
            "model_substitution_permitted": False,
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


def build_plan(
    raw_models: object,
    *,
    limits: RunLimits | None = None,
    prompt_id: str = DEFAULT_PROMPT_ID,
    selection_source: str = "unspecified",
    allow_unconfirmed_aliases: bool = False,
) -> SequentialRunPlan:
    """Validate a selection into a plan, or raise :class:`PlanError`."""
    aliases = parse_model_selection(raw_models)
    unconfirmed = (
        tuple(a for a in aliases if a not in OBSERVED_GATEWAY_ALIASES)
        if allow_unconfirmed_aliases
        else ()
    )
    return SequentialRunPlan(
        model_aliases=aliases,
        limits=limits or RunLimits(),
        prompt_id=prompt_id,
        selection_source=selection_source,
        unconfirmed_aliases=unconfirmed,
    )
